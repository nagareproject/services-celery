# --
# Copyright (c) 2014-2025 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from __future__ import absolute_import

import threading

from celery.bin import events
from celery.backends import asynchronous

from nagare.server import publisher

# ==========
# isort: off

from celery.utils import log


def _get_logger(get_logger, name):
    return get_logger('nagare.services.' + name)


log._get_logger = lambda name, get_logger=log._get_logger: _get_logger(get_logger, name)
log.base_logger = log.logger = log.get_logger('celery')


from celery.app import log


class Logging(log.Logging):
    _setup = True


# ==========
# isort: on

import sys
import multiprocessing

import celery
from celery.app import defaults
from celery.utils import collections
from celery.schedules import crontab

from nagare.server import reference
from nagare.services import proxy, plugin

SPEC_TYPES = {'str': 'string', 'int': 'integer', 'bool': 'boolean'}
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
    'worker task_log_format',
    'beat cron_starting_deadline',  # Bug in Celery 5.3.1
    'security key_password',  # `bytes` type
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

    spec['result']['backend_max_retries'] = 'float(default=float("inf"))'
    spec['result']['expires'] = 'float(default={})'.format(24 * 60 * 60)
    spec['result']['asynchronous_callbacks'] = 'boolean(default=False)'
    spec['broker']['heartbeat_checkrate'] = spec['broker']['heartbeat_checkrate'].replace('integer', 'float')
    spec['worker']['concurrency'] = 'string(default="0")'
    spec['task']['default_delivery_mode'] = spec['task']['default_delivery_mode'].replace('2', 'persistent')
    spec['task']['__many__'] = {'queue': 'string'}

    spec['beat']['__many__'] = dict(
        dict.fromkeys(CRONTAB_PARAMS, 'string(default=None)'),
        task='string',
        schedule='integer(default=None)',
        args='string(default="()")',
    )

    # Task options from https://docs.celeryq.dev/en/stable/userguide/tasks.html#list-of-options
    spec['__many__'] = dict(
        [
            (param + '(default=None)').split('/')
            for param in (
                'bind/boolean',
                'name/string',
                'Request/string',
                'Strategie/string',
                'typing/boolean',
                'autoretry_for/string_list',
                'dont_autoretry_for/string_list',
                'max_retries/integer',
                'retry_backoff/boolean',
                'retry_backoff_max/integer',
                'retry_jitter/boolean',
                'throws/string_list',
                'default_retry_delay/float',
                'rate_limit/string',
                'time_limit/integer',
                'soft_time_limit/integer',
                'ignore_result/boolean',
                'store_errors_even_if_ignored/boolean',
                'serializer/string',
                'compression/string',
                'backend/string',
                'acks_late/boolean',
                'track_started/boolean',
                'trail/boolean',
                'send_events/boolean',
                'ack_on_failure_or_timeout/boolean',
                'reject_on_worker_lost/boolean',
                'expires/float',
                'priority/integer',
                'lazy/boolean',
            )
        ],
        retry_kargs={
            'countdown': 'float(default=None)',
            'max_retries': 'integer(default=None)',
            'throw': 'boolean(default=True)',
        },
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
        name,
        dist,
        config_sections,
        main,
        on_configure,
        watch,
        tasks,
        services_service,
        reloader_service=None,
        **config,
    ):
        """Initialization.

        In:
          - ``host`` -- address of the memcache server
          - ``port`` -- port of the memcache server
        """
        super().__init__(name, dist, **config)

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
                if section not in config_sections:
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
            for exceptions in ['throws', 'autoretry_for', 'dont_autoretry_for']:
                if exceptions in parameters:
                    parameters[exceptions] = [reference.load_object(exc)[0] for exc in parameters[exceptions]]

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

    def serve(self, subcommand, args, **arguments):
        self.services(super().serve)

        if self.watch and (self.reloader is not None):
            for filename in self.files:
                self.reloader.watch_file(filename)

        worker = self.celery.Worker(**arguments)
        worker.start()

        return worker.exitcode

    def beat(self, subcommand, args, **arguments):
        self.celery.Beat(**arguments).run()

    def events(self, subcommand, args, camera, **arguments):
        if camera:
            events._run_evcam(camera, self.celery, **arguments)
        else:
            events._run_evtop(self.celery)

    def status(self, subcommand, args, destination, timeout, **arguments):
        workers = self.inspect('ping', args, destination, timeout, **arguments) or {}

        return {name: ({'ok': ''} if 'ok' in status else status) for name, status in workers.items()}

    def report(self, subcommand, args):
        print(self.celery.bugreport())

    def call(self, subcommand, args, name, args_, **arguments):
        print(self.celery.send_task(name, args_, **arguments))

    def result(self, subcommand, args, task_id, traceback):
        result = self.celery.AsyncResult(task_id)
        print(result.traceback if traceback else result.get())

    def inspect(self, subcommand, args, destination, timeout, reply=True):
        inspect = self.celery.control.inspect(destination, timeout)
        subcommand = getattr(inspect, subcommand)

        return subcommand(*args)

    def control(self, subcommand, args, **arguments):
        control = self.celery.control
        subcommand = getattr(control, subcommand)

        return subcommand(*args, **arguments)


@proxy.proxy_to(_CeleryService, lambda self: self.service, {'handle_request'})
class CeleryService(plugin.Plugin):
    CONFIG_SPEC = (
        _CeleryService.CONFIG_SPEC
        | {
            'main': 'string(default="nagare.application.$app_name")',
            'tasks': 'string_list(default=list())',
            'on_configure': 'string(default=None)',
            'watch': 'boolean(default=True)',
        }
        | create_spec((), defaults.NAMESPACES)
    )
    service = None

    def __init__(self, name, dist, services_service, **config):
        services_service(super().__init__, name, dist, **config)

        config_sections = {section for section, parameters in self.CONFIG_SPEC.items() if isinstance(parameters, dict)}
        self.__class__.service = services_service(_CeleryService, name, dist, config_sections, **config)

    @property
    def AsyncResult(self):
        return self.service.AsyncResult
