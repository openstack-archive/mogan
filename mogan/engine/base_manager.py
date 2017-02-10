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

from eventlet import greenpool
from oslo_service import periodic_task
from oslo_utils import importutils

from mogan.common.i18n import _
from mogan.conf import CONF
from mogan.db import api as dbapi
from mogan.engine import rpcapi
from mogan import network


class BaseEngineManager(periodic_task.PeriodicTasks):

    def __init__(self, host, topic):
        super(BaseEngineManager, self).__init__(CONF)
        if not host:
            host = CONF.host
        self.host = host
        self.topic = topic
        self.node_cache = {}
        self.network_api = network.API()
        scheduler_driver = CONF.scheduler.scheduler_driver
        self.scheduler = importutils.import_object(scheduler_driver)
        self.driver = importutils.import_object(CONF.engine.engine_driver)
        # Now we use engine driver instead of ironicclient here.
        # self.ironicclient = ironic.IronicClientWrapper()
        self.engine_rpcapi = rpcapi.EngineAPI()
        self._sync_power_pool = greenpool.GreenPool(
            size=CONF.engine.sync_power_state_pool_size)
        self._syncs_in_progress = {}
        self._started = False

    def init_host(self):
        """Initialize the engine host.

        :param admin_context: the admin context to pass to periodic tasks.
        :raises: RuntimeError when engine is already running.
        """
        if self._started:
            raise RuntimeError(_('Attempt to start an already running '
                                 'engine manager'))

        self.dbapi = dbapi.get_instance()

        self._worker_pool = greenpool.GreenPool(
            size=CONF.engine.workers_pool_size)

        self._started = True

    def del_host(self):
        self._worker_pool.waitall()
        self._started = False

    def periodic_tasks(self, context, raise_on_error=False):
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)
