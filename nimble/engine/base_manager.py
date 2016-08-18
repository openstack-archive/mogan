# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Base engine manager functionality."""

import inspect

import futurist
from futurist import periodics
from futurist import rejection
from oslo_log import log

from nimble.common import exception
from nimble.common.i18n import _
from nimble.common.i18n import _LC
from nimble.common.i18n import _LI
from nimble.common.i18n import _LW
from nimble.common import rpc
from nimble.conf import CONF
from nimble.db import api as dbapi


LOG = log.getLogger(__name__)


class BaseEngineManager(object):

    def __init__(self, host, topic):
        super(BaseEngineManager, self).__init__()
        if not host:
            host = CONF.host
        self.host = host
        self.topic = topic
        self.notifier = rpc.get_notifier()
        self._started = False

    def init_host(self, admin_context=None):
        """Initialize the engine host.

        :param admin_context: the admin context to pass to periodic tasks.
        :raises: RuntimeError when engine is already running.
        """
        if self._started:
            raise RuntimeError(_('Attempt to start an already running '
                                 'engine manager'))

        self.dbapi = dbapi.get_instance()

        rejection_func = rejection.reject_when_reached(
            CONF.engine.workers_pool_size)
        self._executor = futurist.GreenThreadPoolExecutor(
            max_workers=CONF.engine.workers_pool_size,
            check_and_reject=rejection_func)
        """Executor for performing tasks async."""

        LOG.debug('Collecting periodic tasks')
        self._periodic_task_callables = []
        self._collect_periodic_tasks(self, (admin_context,))

        if (len(self._periodic_task_callables) >
                CONF.engine.workers_pool_size):
            LOG.warning(_LW('This engine has %(tasks)d periodic tasks '
                            'enabled, but only %(workers)d task workers '
                            'allowed by [engine]workers_pool_size option'),
                        {'tasks': len(self._periodic_task_callables),
                         'workers': CONF.engine.workers_pool_size})

        self._periodic_tasks = periodics.PeriodicWorker(
            self._periodic_task_callables,
            executor_factory=periodics.ExistingExecutor(self._executor))

        # Start periodic tasks
        self._periodic_tasks_worker = self._executor.submit(
            self._periodic_tasks.start, allow_empty=True)
        self._periodic_tasks_worker.add_done_callback(
            self._on_periodic_tasks_stop)

    def del_host(self):
        # Waiting here to give workers the chance to finish. This has the
        # benefit of releasing locks workers placed on nodes, as well as
        # having work complete normally.
        self._periodic_tasks.stop()
        self._periodic_tasks.wait()
        self._executor.shutdown(wait=True)
        self._started = False

    def _collect_periodic_tasks(self, obj, args):
        """Collect periodic tasks from a given object.

        Populates self._periodic_task_callables with tuples
        (callable, args, kwargs).

        :param obj: object containing periodic tasks as methods
        :param args: tuple with arguments to pass to every task
        """
        for name, member in inspect.getmembers(obj):
            if periodics.is_periodic(member):
                LOG.debug('Found periodic task %(owner)s.%(member)s',
                          {'owner': obj.__class__.__name__,
                           'member': name})
                self._periodic_task_callables.append((member, args, {}))

    def _on_periodic_tasks_stop(self, fut):
        try:
            fut.result()
        except Exception as exc:
            LOG.critical(_LC('Periodic tasks worker has failed: %s'), exc)
        else:
            LOG.info(_LI('Successfully shut down periodic tasks'))

    def _spawn_worker(self, func, *args, **kwargs):

        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.

        :returns: Future object.
        :raises: NoFreeEgnineWorker if worker pool is currently full.

        """
        try:
            return self._executor.submit(func, *args, **kwargs)
        except futurist.RejectedSubmission:
            raise exception.NoFreeEngineWorker()
