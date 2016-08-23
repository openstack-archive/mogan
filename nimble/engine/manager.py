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

from oslo_log import log
import oslo_messaging as messaging
from oslo_service import periodic_task

from nimble.common.i18n import _LI
from nimble.conf import CONF
from nimble.engine import base_manager

MANAGER_TOPIC = 'nimble.engine_manager'

LOG = log.getLogger(__name__)


class EngineManager(base_manager.BaseEngineManager):
    """Nimble Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval)
    def _sync_node_resources(self, context):
        LOG.info(_LI("During sync_node_resources."))

    def create_instance(self, context, instance):
        """Signal to engine service to perform a deployment."""
        LOG.debug("During create instance.")
        instance.task_state = 'deploying'
        instance.save()
        return instance
