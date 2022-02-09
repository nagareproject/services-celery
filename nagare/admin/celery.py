# --
# Copyright (c) 2008-2022 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

from json import loads, dumps
from nagare.admin import command


class Commands(command.Commands):
    DESC = 'Celery server subcommands'


class Command(command.Command):

    def run(self, command, args=(), **params):
        return command(self.name.replace('-', '_'), args, **params)


class CommandWithReply(Command):

    def set_arguments(self, parser):
        parser.add_argument(
            '-t', '--timeout',
            type=float, default=1.0,
            help='timeout in seconds (float) waiting for reply'
        )
        parser.add_argument(
            '-d', '--destination',
            action='append',
            help='destination node name'
        )
        parser.add_argument('-q', '--quiet', action='store_true', help="don't display anything")
        parser.add_argument('-j', '--json', action='store_true', help='use json as output format')

        super(CommandWithReply, self).set_arguments(parser)

    @staticmethod
    def print_result(workers):
        for worker, status in sorted(workers.items()):
            ko = (status is not None) and isinstance(status, dict) and ('error' in status)

            print('{}: {}'.format(worker, 'ERROR' if ko else 'OK'))
            if not status:
                print('- empty -')
            else:
                if isinstance(status, list):
                    for stats in status:
                        print('    *', stats)

                if isinstance(status, dict):
                    lines = status.get('ok', status.get('error'))
                    if lines is not None:
                        for line in lines.splitlines():
                            print('    ' + line)
                    else:
                        print(dumps(status, sort_keys=True, indent=4))

            print('')

    def run(self, command, args, json, quiet, **arguments):
        workers = super(CommandWithReply, self).run(command, args, reply=True, **arguments)
        if workers is None:
            if not quiet:
                print('Error: No nodes replied within time constraint')

            return 2

        if isinstance(workers, dict):
            workers = [workers]

        nb = sum(len(worker) for worker in workers)

        if not quiet:
            if json:
                print(dumps(workers))
            else:
                for worker in workers:
                    self.print_result(worker)

                print('{} node{} online.'.format(nb, 's' if nb > 1 else ''))

        return not nb


class Serve(Command):
    DESC = 'start worker instance'

    def set_arguments(self, parser):
        parser.add_argument('-q', '--quiet', action='store_true', help="don't display anything")
        parser.add_argument('-c', '--no-color', action='store_true')
        parser.add_argument(
            '-Q', '--queues',
            help='list of queues to enable for this worker, separated by comma'
        )
        parser.add_argument(
            '-X', '--exclude-queues',
            help='list of queues to exclude for this worker, separated by comma'
        )

        super(Serve, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Serve, self).run(celery_service.serve, **arguments)


class Beat(Command):
    DESC = 'start the beat periodic task scheduler'

    def set_arguments(self, parser):
        parser.add_argument('-i', '--interval', type=int, dest='max_interval')
        parser.add_argument('-c', '--no-color', action='store_true')
        parser.add_argument('--db', help='db file name', dest='schedule')
        parser.add_argument(
            '-t', '--timeout',
            type=float, default='10', dest='socket_timeout'
        )

        super(Beat, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Beat, self).run(celery_service.beat, **arguments)


class Events(Command):
    DESC = 'start event-stream monitor'

    def set_arguments(self, parser):
        parser.add_argument('-c', '--camera', help='take snapshots of events using this camera')
        parser.add_argument(
            '-f', '--frequency', '--freq',
            type=float, default='1.0', dest='freq',
            help='camera shutter frequency. Default is every 1.0 secondes'
        )
        parser.add_argument('-r', '--maxrate', help='camerao optional shutter rate limit (e.g., 10/m)')

        super(Events, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Events, self).run(celery_service.events, **arguments)


class Status(CommandWithReply):
    DESC = 'show list of workers that are online'

    def run(self, celery_service, **arguments):
        return super(Status, self).run(celery_service.status, (), **arguments)


class Report(Command):
    DESC = 'shows information useful to include in bug-reports'

    def run(self, celery_service, **arguments):
        return super(Report, self).run(celery_service.report, (), **arguments)


class Call(Command):
    DESC = 'call a task by name'

    def set_arguments(self, parser):
        parser.add_argument('name', help='task name')
        parser.add_argument('-a', '--args', dest='args_', help='positional arguments (list or tuple in json format)')
        parser.add_argument('-k', '--kwargs', help='keyword arguments (dict in json format)')
        parser.add_argument('-c', '--countdown', help='eta in seconds from now')
        parser.add_argument('-q', '--queue', help='custom queue name')
        parser.add_argument('-x', '--exchange', help='custom exchange name')
        parser.add_argument('-r', '--routing-key', help='custom routing key')

        super(Call, self).set_arguments(parser)

    def run(self, celery_service, args_, kwargs, **arguments):
        return super(Call, self).run(
            celery_service.call,
            (),
            args_=() if args_ is None else loads(args_),
            kwargs={} if kwargs is None else loads(kwargs),
            **arguments
        )


class Result(Command):
    DESC = 'print the return value for a given task id'

    def set_arguments(self, parser):
        parser.add_argument('task_id', help='task id')
        parser.add_argument('-t', '--traceback', action='store_true', help='print traceback instead')

        super(Result, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Result, self).run(celery_service.result, (), **arguments)

# ==========


class Inspect(command.Commands):
    DESC = 'reporting commands'


class InspectCommand(CommandWithReply):

    def run(self, celery_service, args=(), **params):
        return super(InspectCommand, self).run(celery_service.inspect, args, **params)


class InspectActive(InspectCommand):
    DESC = 'list of tasks currently being executed'


class InspectActiveQueues(InspectCommand):
    DESC = 'list the task queues a worker is currently consuming from'


class InspectClock(InspectCommand):
    DESC = 'get current logical clock value'


class InspectConf(InspectCommand):
    DESC = 'list configuration'

    def set_arguments(self, parser):
        parser.add_argument('-i', '--include', action='store_true', help='include default values')

        super(InspectConf, self).set_arguments(parser)

    def run(self, celery_service, include, **arguments):
        return super(InspectConf, self).run(celery_service, [include], **arguments)


class InspectPing(InspectCommand):
    DESC = 'ping worker(s)'


class InspectQueryTask(InspectCommand):
    DESC = 'query for task information by id'

    def set_arguments(self, parser):
        parser.add_argument(
            '-i', '--id',
            action='append', dest='ids',
            help='task identifier'
        )

        super(InspectQueryTask, self).set_arguments(parser)

    def run(self, celery_service, ids, **arguments):
        return super(InspectQueryTask, self).run(celery_service, ids or [], **arguments)


class InspectRegistered(InspectCommand):
    DESC = 'list registered tasks'

    def set_arguments(self, parser):
        parser.add_argument(
            '-a', '--attr',
            action='append', dest='attributes',
            help='task attribute to include'
        )

        super(InspectRegistered, self).set_arguments(parser)

    def run(self, celery_service, attributes, **arguments):
        return super(InspectRegistered, self).run(celery_service, attributes or [], **arguments)


class InspectReport(InspectCommand):
    DESC = 'information about Celery installation for bug reports'


class InspectReserved(InspectCommand):
    DESC = 'list currently reserved tasks, not including scheduled/active'


class InspectRevoked(InspectCommand):
    DESC = 'list of revoked task-ids'


class InspectScheduled(InspectCommand):
    DESC = 'list of currently scheduled ETA/countdown tasks'


class InspectStats(InspectCommand):
    DESC = 'request worker statistics/information'

# ==========


class Control(command.Commands):
    DESC = 'control commands'


class ControlCommand(Command):

    def run(self, celery_service, args=(), **params):
        return super(ControlCommand, self).run(celery_service.control, args, **params)


class ControlCommandWithReply(CommandWithReply):

    def run(self, celery_service, args=(), **params):
        return super(ControlCommandWithReply, self).run(celery_service.control, args, **params)


class ControlAddConsumer(ControlCommandWithReply):
    DESC = 'tell worker(s) to consume from task queue by name'

    def set_arguments(self, parser):
        parser.add_argument('queue')
        parser.add_argument('-x', '--exchange')
        parser.add_argument('-e', '--exchange-type')
        parser.add_argument('-r', '--routing_key')

        super(ControlAddConsumer, self).set_arguments(parser)

    def run(self, celery_service, queue, exchange, exchange_type, routing_key, **arguments):
        return super(ControlAddConsumer, self).run(
            celery_service,
            args=[queue, exchange, exchange_type, routing_key],
            **arguments
        )


class ControlAutoscale(ControlCommandWithReply):
    DESC = 'modify autoscale settings'

    def set_arguments(self, parser):
        parser.add_argument('max', type=int)
        parser.add_argument('min', type=int)

        super(ControlAutoscale, self).set_arguments(parser)

    def run(self, celery_service, max, min, **arguments):
        return super(ControlAutoscale, self).run(celery_service, [max, min], **arguments)


class ControlCancelConsumer(ControlCommandWithReply):
    DESC = 'tell worker(s) to stop consuming from task queue by name'

    def set_arguments(self, parser):
        parser.add_argument('queue')

        super(ControlCancelConsumer, self).set_arguments(parser)

    def run(self, celery_service, queue, **arguments):
        return super(ControlCancelConsumer, self).run(celery_service, [queue], **arguments)


class ControlDisableEvents(ControlCommandWithReply):
    DESC = 'tell worker(s) to stop sending task-related events'


class ControlElection(ControlCommand):
    DESC = 'hold election'

    def set_arguments(self, parser):
        parser.add_argument('id')
        parser.add_argument('topic')

        super(ControlElection, self).set_arguments(parser)


class ControlEnableEvents(ControlCommandWithReply):
    DESC = 'tell worker(s) to send task-related events'


class ControlHeartbeat(ControlCommandWithReply):
    DESC = 'tell worker(s) to send event heartbeat immediately'


class ControlPoolGrow(ControlCommandWithReply):
    DESC = 'grow pool by nb processes/threads'

    def set_arguments(self, parser):
        parser.add_argument('nb', type=int)

        super(ControlPoolGrow, self).set_arguments(parser)

    def run(self, celery_service, nb, **arguments):
        return super(ControlPoolGrow, self).run(celery_service, [nb], **arguments)


class ControlPoolRestart(ControlCommandWithReply):
    DESC = 'restart execution pool'

    def set_arguments(self, parser):
        parser.add_argument('-m', '--module', action='append', dest='modules')
        parser.add_argument('-r', '--reload', action='store_true')

        super(ControlPoolRestart, self).set_arguments(parser)


class ControlPoolShrink(ControlCommandWithReply):
    DESC = 'shrink pool by nb processes/thread'

    def set_arguments(self, parser):
        parser.add_argument('nb', type=int)

        super(ControlPoolShrink, self).set_arguments(parser)

    def run(self, celery_service, nb, **arguments):
        return super(ControlPoolShrink, self).run(celery_service, [nb], **arguments)


class ControlRateLimit(ControlCommandWithReply):
    DESC = 'tell worker(s) to modify the rate limit for a task'

    def set_arguments(self, parser):
        parser.add_argument('task')
        parser.add_argument('rate_limit', help='e.g. 5/s | 5/m | 5/h')

        super(ControlRateLimit, self).set_arguments(parser)

    def run(self, celery_service, task, rate_limit, **arguments):
        return super(ControlRateLimit, self).run(celery_service, [task, rate_limit], **arguments)


class ControlRevoke(ControlCommandWithReply):
    DESC = 'revoke task by task id (or list of ids)'

    def set_arguments(self, parser):
        parser.add_argument('-i', '--id', action='append', help='task id', dest='ids')

        super(ControlRevoke, self).set_arguments(parser)

    def run(self, celery_service, ids, **arguments):
        return super(ControlRevoke, self).run(celery_service, [ids or []], **arguments)


class ControlShutdown(ControlCommandWithReply):
    DESC = 'shutdown worker(s)'


class ControlTerminate(ControlCommandWithReply):
    DESC = 'terminate task by task id (or list of ids)'

    def set_arguments(self, parser):
        parser.add_argument('-s', '--signal', type=int)
        parser.add_argument('-i', '--id', action='append', help='task id', dest='ids')

        super(ControlTerminate, self).set_arguments(parser)

    def run(self, celery_service, signal, ids, **arguments):
        return super(ControlTerminate, self).run(celery_service, [ids or []], signal=signal, **arguments)


class ControlTimeLimit(ControlCommandWithReply):
    DESC = 'tell worker(s) to modify the time limit for task'

    def set_arguments(self, parser):
        parser.add_argument('task_name')
        parser.add_argument('soft_secs')
        parser.add_argument('hard_secs')

        super(ControlTimeLimit, self).set_arguments(parser)

    def run(self, celery_service, task_name, soft_secs, hard_secs, **arguments):
        return super(ControlTimeLimit, self).run(celery_service, [task_name, soft_secs, hard_secs], **arguments)


class Purge(ControlCommand):
    DESC = 'erase all messages from all known task queues'
