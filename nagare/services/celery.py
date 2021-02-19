# --
# Copyright (c) 2008-2020 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from __future__ import absolute_import

import threading

from nagare.server import publisher
from celery.backends import asynchronous

# ==========

from celery.utils import log


def _get_logger(get_logger, name):
    return get_logger('nagare.services.' + name)


log._get_logger = lambda name, get_logger=log._get_logger: _get_logger(get_logger, name)
log.base_logger = log.logger = log.get_logger('celery')


from celery.app import log


class Logging(log.Logging):
    _setup = True

# ==========


import sys
import multiprocessing

import celery
from celery.app import defaults
from celery.utils import collections
from celery.schedules import crontab
from celery.bin import celery as command

from nagare.server import reference
from nagare.services import plugin, proxy

SPEC_TYPES = {'int': 'integer', 'bool': 'boolean'}
CRONTAB_PARAMS = ('minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')
BLACK_LIST = {
    'arangodb',
    'cassandra auth_kwargs',
    'couchbase',
    'mongodb',
    'riak',
    'task annotations',
    'task routes',
    'worker log_format',
    'worker task_log_format'
}


def create_spec_from_celery(namespace_name, namespace):
    new_spec = {}
    for name, spec in namespace.items():
        fullname = namespace_name + (name,)
        if ' '.join(fullname) in BLACK_LIST:
            continue

        if isinstance(spec, dict):
            r = create_spec_from_celery(fullname, spec)
        elif isinstance(spec, int):
            r = 'integer(default={})'.format(spec)
        elif isinstance(spec, float):
            r = 'float(default={})'.format(spec)
        elif (spec.type == 'dict') and not spec.default:
            continue
        elif isinstance(spec, dict):
            r = create_spec_from_celery(fullname, spec)
        elif spec.type == 'dict':
            r = create_spec_from_celery(fullname, spec.default)
        else:
            if isinstance(spec.default, str):
                default = '"{}"'.format(spec.default)
            elif isinstance(spec.default, (list, tuple)):
                default = 'list({})'.format(','.join('"{}"'.format(x) for x in spec.default))
            else:
                default = spec.default

            r = '{}(default={})'.format(SPEC_TYPES.get(spec.type, spec.type), default)

        new_spec[name] = r

    return new_spec


def create_spec(namespace_name, namespace):
    spec = create_spec_from_celery(namespace_name, namespace)

    spec['result']['expires'] = 'float(default={})'.format(24 * 60 * 60)
    spec['result']['asynchronous_callbacks'] = 'boolean(default=False)'
    spec['broker']['heartbeat_checkrate'] = spec['broker']['heartbeat_checkrate'].replace('integer', 'float')
    spec['worker']['concurrency'] = 'string(default="0")'
    spec['task']['default_delivery_mode'] = spec['task']['default_delivery_mode'].replace('2', 'persistent')
    spec['task']['__many__'] = {'queue': 'string'}

    spec['beat']['__many__'] = dict(
        {name: 'string(default=None)' for name in CRONTAB_PARAMS},
        task='string',
        schedule='integer(default=None)',
        args='string(default="")'
    )

    spec['__many__'] = dict(
        (param + '(default=None)').split('/') for param in (
            'Strategie/string', 'typing/boolean', 'Request/string', 'trail/boolean',
            'send_events/boolean', 'ack_on_failure_or_timeout/boolean',
            'reject_on_worker_lost/boolean', 'expires/float', 'priority/integer',
            'name/string', 'max_retries/integer', 'default_retry_delay/float', 'rate_limit/string',
            'time_limit/integer', 'soft_time_limit/integer', 'ignore_result/boolean',
            'store_errors_even_if_ignored/boolean', 'serializer/string', 'compression/string',
            'backend/string', 'acks_late/boolean', 'track_started/boolean', 'lazy/boolean',
            'bind/boolean', 'retry_backoff/boolean', 'retry_backoff_max/integer', 'retry_jitter/boolean'
        )
    )

    return spec


class Drainer(asynchronous.greenletDrainer):

    def spawn(self, run):
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        return thread


class _CeleryService(publisher.Publisher):
    CELERY_FACTORY = celery.Celery

    def __init__(
        self,
        name, dist, config_sections,
        main, on_configure, watch, tasks,
        services_service, reloader_service=None,
        **config
    ):
        """Initialization

        In:
          - ``host`` -- address of the memcache server
          - ``port`` -- port of the memcache server
        """
        super(_CeleryService, self).__init__(name, dist, **config)

        self.watch = watch
        self.reloader = reloader_service
        self.services = services_service
        self.files = set()

        nb_cpus = multiprocessing.cpu_count()
        config['worker']['concurrency'] = eval(config['worker']['concurrency'], {}, {'NB_CPUS': nb_cpus})

        celery_config = {}
        app_tasks = {name: {} for name in tasks}

        for section, parameters in list(config.items()):
            if isinstance(parameters, dict):
                if (section not in config_sections):
                    app_tasks[section] = config[section] = {k: v for k, v in parameters.items() if v is not None}
                else:
                    celery_config[section] = parameters.copy()
            else:
                celery_config[section] = parameters

        celery_config['task']['routes'] = {
            section: celery_config['task'].pop(section)['queue']
            for section, parameters in list(celery_config['task'].items())
            if isinstance(parameters, dict) and (section != 'publish_retry_policy')
        }

        schedules = {}
        for section, parameters in list(celery_config['beat'].items()):
            if isinstance(parameters, dict):
                del celery_config['beat'][section]

                schedule = {'task': parameters['task'], 'args': eval(parameters['args'])}

                if parameters['schedule']:
                    schedule['schedule'] = parameters['schedule']

                crontab_params = {param: parameters[param] for param in CRONTAB_PARAMS if parameters[param] is not None}
                if crontab_params:
                    schedule['schedule'] = crontab(**crontab_params)

                schedules[section] = schedule

        celery_config = collections.AttributeDict(defaults.flatten(celery_config))
        celery_config['beat_schedule'] = schedules

        if celery_config.pop('result_asynchronous_callbacks'):
            asynchronous.register_drainer('default')(Drainer)

        if on_configure:
            reference.load_object(on_configure)[0](celery_config)

        self.celery = self.CELERY_FACTORY(main, log='nagare.services.celery:Logging', config_source=celery_config)

        for task, parameters in app_tasks.items():
            self.register_task(reference.load_object(task)[0], **parameters)

    @property
    def AsyncResult(self):
        return self.celery.AsyncResult

    def register_task(self, f, **kw):
        task = self.celery.task(**kw)(f)

        module = sys.modules[f.__module__]
        self.files.add(module.__file__)
        setattr(module, f.__name__, task)

    def print_banner(self):
        pass

    def serve(self, no_color, quiet, **arguments):
        self.services(super(_CeleryService, self).serve)

        if self.watch and (self.reloader is not None):
            for filename in self.files:
                self.reloader.watch_file(filename)

        worker = self.celery.Worker(no_color=no_color, quiet=quiet, **arguments)
        worker.start()

        return worker.exitcode

    def beat(self, no_color, quiet, **arguments):
        self.celery.Beat(no_color=no_color, quiet=quiet, **arguments).run()

    def events(self, no_color, quiet, **arguments):
        command.events(self.celery).run(no_color=no_color, quiet=quiet, **arguments)

    def status(self, no_color, quiet, **arguments):
        command.status(self.celery).run(no_color=no_color, quiet=quiet, **arguments)

    def purge(self, no_color, quiet, **arguments):
        command.purge(self.celery).run(no_color=no_color, quiet=quiet, **arguments)

    def list(self, no_color, quiet, bindings):
        command.list_(self.celery).run(no_color=no_color, quiet=quiet, what=bindings)

    def report(self, no_color, quiet):
        command.report(self.celery).run(no_color=no_color, quiet=quiet)

    def inspect(self, subcommand, no_color, quiet, *args, **arguments):
        inspect = command.inspect(self.celery)
        inspect.no_color = no_color
        inspect.quiet = quiet
        inspect.run(subcommand, *args, **arguments)

    def control(self, subcommand, no_color, quiet, *args, **arguments):
        control = command.control(self.celery)
        control.no_color = no_color
        control.quiet = quiet
        control.run(subcommand, *args, **arguments)


@proxy.proxy_to(_CeleryService, lambda self: self.service, {'handle_start'})
class CeleryService(plugin.Plugin):
    CONFIG_SPEC = dict(
        _CeleryService.CONFIG_SPEC,
        main='string(default=nagare.application.$app_name)',
        tasks='list(default=list())',
        on_configure='string(default=None)',
        watch='boolean(default=True)',
        **create_spec((), defaults.NAMESPACES)
    )
    service = None

    def __init__(self, name, dist, services_service, **config):
        services_service(super(CeleryService, self).__init__, name, dist, **config)

        config_sections = {section for section, parameters in self.CONFIG_SPEC.items() if isinstance(parameters, dict)}
        self.__class__.service = services_service(_CeleryService, name, dist, config_sections, **config)

    @property
    def AsyncResult(self):
        return self.service.AsyncResult
