# Encoding: utf-8

# --
# Copyright (c) 2008-2020 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from os import path

from setuptools import setup, find_packages


here = path.normpath(path.dirname(__file__))

with open(path.join(here, 'README.rst')) as long_description:
    LONG_DESCRIPTION = long_description.read()

setup(
    name='nagare-services-celery',
    author='Net-ng',
    author_email='alain.poirier@net-ng.com',
    description='Celery service',
    long_description=LONG_DESCRIPTION,
    license='BSD',
    keywords='',
    url='https://github.com/nagareproject/services-celery',
    packages=find_packages(),
    zip_safe=False,
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    install_requires=['celery', 'nagare-server'],

    # Not working because 'celery' default package is already into 'install_require'.
    # PIP bug: https://github.com/pypa/pip/issues/4957
    extras_require={
        'auth': ['celery[auth]'],
        'msgpack': ['celery[msgpack]'],
        'yaml': ['celery[yaml]'],
        'eventlet': ['celery[eventlet]'],
        'gevent': ['celery[gevent]'],
        'librabbitmq': ['celery[librabbitmq]'],
        'redis': ['celery[redis]'],
        'sqs': ['celery[sqs]'],
        'tblib': ['celery[tblib]'],
        'memcache': ['celery[memcache]'],
        'pymemcache': ['celery[pymemcache]'],
        'cassandra': ['celery[cassandra]'],
        'couchbase': ['celery[couchbase]'],
        'arangodb': ['celery[arangodb]'],
        'elasticsearch': ['celery[elasticsearch]'],
        'riak': ['celery[riak]'],
        'dynamodb': ['celery[dynamodb]'],
        'zookeeper': ['celery[zookeeper]'],
        'sqlalchemy': ['celery[sqlalchemy]'],
        'pyro': ['celery[pyro]'],
        'slmq': ['celery[slmq]'],
        'consul': ['celery[consul]']
    },

    entry_points={
        'nagare.commands': [
            'celery=nagare.admin.celery:Commands'
        ],

        'nagare.commands.celery': [
            'serve=nagare.admin.celery:Serve',
            'beat=nagare.admin.celery:Beat',
            'events=nagare.admin.celery:Events',
            'status=nagare.admin.celery:Status',
            'inspect=nagare.admin.celery:Inspect',
            'control=nagare.admin.celery:Control',
            'purge=nagare.admin.celery:Purge',
            'list=nagare.admin.celery:List',
            'report=nagare.admin.celery:Report'
        ],

        'nagare.commands.celery.inspect': [
            'report=nagare.admin.celery:InspectReport',
            'conf=nagare.admin.celery:InspectConf',
            'query-task=nagare.admin.celery:InspectQueryTask',
            'clock=nagare.admin.celery:InspectClock',
            'ping=nagare.admin.celery:InspectPing',
            'stats=nagare.admin.celery:InspectStats',
            'scheduled=nagare.admin.celery:InspectScheduled',
            'reserved=nagare.admin.celery:InspectReserved',
            'active=nagare.admin.celery:InspectActive',
            'revoked=nagare.admin.celery:InspectRevoked',
            'registered=nagare.admin.celery:InspectRegistered',
            'active-queues=nagare.admin.celery:InspectActiveQueues'
        ],

        'nagare.commands.celery.control': [
            'revoke=nagare.admin.celery:ControlRevoke',
            'terminate=nagare.admin.celery:ControlTerminate',
            'rate-limit=nagare.admin.celery:ControlRateLimit',
            'time-limit=nagare.admin.celery:ControlTimeLimit',
            'election=nagare.admin.celery:ControlElection',
            'enable-events=nagare.admin.celery:ControlEnableEvents',
            'disable-events=nagare.admin.celery:ControlDisableEvents',
            'heartbeat=nagare.admin.celery:ControlHeartbeat',
            'pool-grow=nagare.admin.celery:ControlPoolGrow',
            'pool-shrink=nagare.admin.celery:ControlPoolShrink',
            'pool-restart=nagare.admin.celery:ControlPoolRestart',
            'autoscale=nagare.admin.celery:ControlAutoscale',
            'shutdown=nagare.admin.celery:ControlShutdown',
            'add-consumer=nagare.admin.celery:ControlAddConsumer',
            'cancel-consumer=nagare.admin.celery:ControlCancelConsumer'
        ],

        'nagare.services': [
            'celery=nagare.services.celery:CeleryService'
        ]
    }
)
