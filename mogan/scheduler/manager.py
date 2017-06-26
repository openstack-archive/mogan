# Copyright 2017 Huawei Technologies Co.,LTD.
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

import eventlet
import oslo_messaging as messaging
from oslo_service import periodic_task
from oslo_utils import importutils

from mogan.common import exception
from mogan.conf import CONF


class SchedulerManager(periodic_task.PeriodicTasks):
    """Mogan Scheduler manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, topic, host=None):
        super(SchedulerManager, self).__init__(CONF)
        self.host = host or CONF.host
        self.topic = topic
        scheduler_driver = CONF.scheduler.scheduler_driver
        self.driver = importutils.import_object(scheduler_driver)
        self._startup_delay = True

    def init_host(self):
        self._startup_delay = False

    def _wait_for_scheduler(self):
        while self._startup_delay and not self.driver.is_ready():
            eventlet.sleep(1)

    @messaging.expected_exceptions(exception.NoValidNode)
    def select_destinations(self, ctxt, request_spec, filter_properties):
        self._wait_for_scheduler()
        dests = self.driver.schedule(
            ctxt, request_spec, filter_properties)
        return dests

    def periodic_tasks(self, context, raise_on_error=False):
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)
