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

from celery.app import Celery
from celery.bin import control

from nagare.admin import celery

inspect_commands = []
for command_name in control.inspect(Celery()).choices:
    class_name = 'Inspect' + command_name.replace('_', ' ').title().replace(' ', '')
    if hasattr(celery, class_name):
        inspect_commands.append('{}=nagare.admin.celery:{}'.format(command_name.replace('_', '-'), class_name))

control_commands = []
for command_name in control.control(Celery()).choices:
    class_name = 'Control' + command_name.replace('_', ' ').title().replace(' ', '')
    if hasattr(celery, class_name):
        control_commands.append('{}=nagare.admin.celery:{}'.format(command_name.replace('_', '-'), class_name))

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

        'nagare.commands.celery.inspect': inspect_commands,

        'nagare.commands.celery.control': control_commands,

        'nagare.services': [
            'celery=nagare.services.celery:CeleryService'
        ]
    }
)
