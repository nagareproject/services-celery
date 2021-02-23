# --
# Copyright (c) 2008-2021 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --
from functools import partial
from nagare.admin import command


class Commands(command.Commands):
    DESC = 'Celery server subcommands'


class Command(command.Command):

    def set_arguments(self, parser):
        parser.add_argument('-c', '--no-color', action='store_true')
        parser.add_argument('-q', '--quiet', action='store_true')

        super(Command, self).set_arguments(parser)

    def run(self, method, no_color, quiet, args=(), **arguments):
        return method(no_color, quiet, *args, **arguments)


class Serve(Command):
    DESC = 'start worker instance'

    def set_arguments(self, parser):
        parser.add_argument(
            '-Q', '--queues',
            help='list of queues to enable for this worker, separated by comma'
        )
        super(Serve, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Serve, self).run(celery_service.serve, **arguments)


class Beat(Command):
    DESC = 'start the beat periodic task scheduler'

    def run(self, celery_service, **arguments):
        return super(Beat, self).run(celery_service.beat, **arguments)


class Events(Command):
    DESC = 'start event-stream monitor'

    def set_arguments(self, parser):
        parser.add_argument('-camera', help='take snapshots of events using this camera')
        parser.add_argument(
            '-f', '--frequency', '--freq',
            type=float, default='1.0',
            help='camera shutter frequency. Default is every 1.0 secondes'
        )
        parser.add_argument('-r', '--maxrate', help='camerao optional shutter rate limit (e.g., 10/m)')

        super(Events, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Events, self).run(celery_service.events, **arguments)


class Status(Command):
    DESC = 'show list of workers that are online'

    def run(self, celery_service, **arguments):
        return super(Status, self).run(celery_service.status, **arguments)


class Purge(Command):
    DESC = 'erase all messages from all known task queues'

    def set_arguments(self, parser):
        parser.add_argument('-f', '--force', help="don't prompt for verification", action='store_true')
        parser.add_argument(
            '-Q', '--queues',
            help='comma separated list of queue names to purge'
        )
        parser.add_argument(
            '-X', '--exclude-queues',
            help='comma separated list of queues names not to purge'
        )

        super(Purge, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(Purge, self).run(celery_service.purge, **arguments)


class List(Command):
    DESC = 'get info from broker'

    def set_arguments(self, parser):
        parser.add_argument('bindings')

        super(List, self).set_arguments(parser)

    def run(self, celery_service, **arguments):
        return super(List, self).run(celery_service.list, **arguments)


class Report(Command):
    DESC = 'shows information useful to include in bug-reports'

    def run(self, celery_service, **arguments):
        return super(Report, self).run(celery_service.report, **arguments)

# ==========


class Inspect(command.Commands):
    DESC = 'reporting commands'


class InspectCommand(Command):

    def set_arguments(self, parser):
        parser.add_argument('-t', '--timeout', type=float, help='timeout in seconds (float) waiting for reply')
        parser.add_argument('-d', '--destination', help='comma separated list of destination node names')

        super(InspectCommand, self).set_arguments(parser)

    def run(self, celery_service, args=(), **arguments):
        return super(InspectCommand, self).run(
            partial(celery_service.inspect, self.name.replace('-', '_')),
            args=args,
            **arguments
        )


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

    def set_arguments(self, parser):
        parser.add_argument('--timeout', type=float, help='timeout in seconds (float) waiting for reply')
        parser.add_argument('-d', '--destination', help='comma separated list of destination node names')

        super(ControlCommand, self).set_arguments(parser)

    def run(self, celery_service, args=(), **arguments):
        return super(ControlCommand, self).run(
            partial(celery_service.control, self.name.replace('-', '_')),
            args=args,
            **arguments
        )


class ControlAddConsumer(ControlCommand):
    DESC = 'tell worker(s) to consume from task queue by name'

    def set_arguments(self, parser):
        parser.add_argument('queue')
        parser.add_argument('-e', '--exchange')
        parser.add_argument('-t', '--exchange-type')
        parser.add_argument('-r', '--routing_key')

        super(ControlAddConsumer, self).set_arguments(parser)

    def run(self, celery_service, queue, exchange, exchange_type, routing_key, **arguments):
        return super(ControlAddConsumer, self).run(
            celery_service,
            args=[queue, exchange, exchange_type, routing_key],
            **arguments
        )


class ControlAutoscale(ControlCommand):
    DESC = 'modify autoscale settings'

    def set_arguments(self, parser):
        parser.add_argument('max')
        parser.add_argument('min')

        super(ControlAutoscale, self).set_arguments(parser)

    def run(self, celery_service, max, min, **arguments):
        return super(ControlAutoscale, self).run(celery_service, [max, min], **arguments)


class ControlCancelConsumer(ControlCommand):
    DESC = 'tell worker(s) to stop consuming from task queue by name'

    def set_arguments(self, parser):
        parser.add_argument('queue')

        super(ControlCancelConsumer, self).set_arguments(parser)

    def run(self, celery_service, queue, **arguments):
        return super(ControlCancelConsumer, self).run(celery_service, [queue], **arguments)


class ControlDisableEvents(ControlCommand):
    DESC = 'tell worker(s) to stop sending task-related events'


class ControlElection(ControlCommand):
    DESC = 'hold election'


class ControlEnableEvents(ControlCommand):
    DESC = 'tell worker(s) to send task-related events'


class ControlHeartbeat(ControlCommand):
    DESC = 'tell worker(s) to send event heartbeat immediately'


class ControlPoolGrow(ControlCommand):
    DESC = 'grow pool by nb processes/threads'

    def set_arguments(self, parser):
        parser.add_argument('nb')

        super(ControlPoolGrow, self).set_arguments(parser)

    def run(self, celery_service, nb, **arguments):
        return super(ControlPoolGrow, self).run(celery_service, [nb], **arguments)


class ControlPoolRestart(ControlCommand):
    DESC = 'restart execution pool'


class ControlPoolShrink(ControlCommand):
    DESC = 'shrink pool by nb processes/thread'

    def set_arguments(self, parser):
        parser.add_argument('nb')

        super(ControlPoolShrink, self).set_arguments(parser)

    def run(self, celery_service, nb, **arguments):
        return super(ControlPoolShrink, self).run(celery_service, [nb], **arguments)


class ControlRateLimit(ControlCommand):
    DESC = 'tell worker(s) to modify the rate limit for a task'

    def set_arguments(self, parser):
        parser.add_argument('task')
        parser.add_argument('rate_limit', help='e.g. 5/s | 5/m | 5/h')

        super(ControlRateLimit, self).set_arguments(parser)

    def run(self, celery_service, task, rate_limit, **arguments):
        return super(ControlRateLimit, self).run(celery_service, [task, rate_limit], **arguments)


class ControlRevoke(ControlCommand):
    DESC = 'revoke task by task id (or list of ids)'

    def set_arguments(self, parser):
        parser.add_argument('-i', '--id', action='append', help='task id', dest='ids')

        super(ControlRevoke, self).set_arguments(parser)

    def run(self, celery_service, ids, **arguments):
        return super(ControlRevoke, self).run(celery_service, [ids or []], **arguments)


class ControlShutdown(ControlCommand):
    DESC = 'shutdown worker(s)'


class ControlTerminate(ControlCommand):
    DESC = 'terminate task by task id (or list of ids)'

    def set_arguments(self, parser):
        parser.add_argument('signal')
        parser.add_argument('-i', '--id', action='append', help='task id', dest='ids')

        super(ControlTerminate, self).set_arguments(parser)

    def run(self, celery_service, signal, ids, **arguments):
        return super(ControlTerminate, self).run(celery_service, [signal, (ids or [])], **arguments)


class ControlTimeLimit(ControlCommand):
    DESC = 'tell worker(s) to modify the time limit for task'

    def set_arguments(self, parser):
        parser.add_argument('task_name')
        parser.add_argument('soft_secs')
        parser.add_argument('hard_secs')

        super(ControlTimeLimit, self).set_arguments(parser)

    def run(self, celery_service, task_name, soft_secs, hard_secs, **arguments):
        return super(ControlTimeLimit, self).run(celery_service, [task_name, soft_secs, hard_secs], **arguments)
