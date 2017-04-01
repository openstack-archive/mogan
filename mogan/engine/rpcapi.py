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
"""
Client side of the engine RPC API.
"""
from oslo_config import cfg
import oslo_messaging as messaging

from mogan.common import constants
from mogan.common import rpc
from mogan.objects import base as objects_base

CONF = cfg.CONF


class EngineAPI(object):
    """Client side of the engine RPC API.

    API version history:

    |    1.0 - Initial version.

    """

    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(EngineAPI, self).__init__()
        self.topic = topic
        if self.topic is None:
            self.topic = constants.ENGINE_TOPIC

        target = messaging.Target(topic=self.topic,
                                  version='1.0')
        serializer = objects_base.MoganObjectSerializer()
        self.client = rpc.get_client(target,
                                     version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)

    def create_instance(self, context, instance, requested_networks,
                        request_spec, filter_properties):
        """Signal to engine service to perform a deployment."""
        cctxt = self.client.prepare(topic=self.topic, server=CONF.host)
        cctxt.cast(context, 'create_instance', instance=instance,
                   requested_networks=requested_networks,
                   request_spec=request_spec,
                   filter_properties=filter_properties)

    def delete_instance(self, context, instance):
        """Signal to engine service to delete an instance."""
        cctxt = self.client.prepare(topic=self.topic, server=CONF.host)
        cctxt.cast(context, 'delete_instance', instance=instance)

    def set_power_state(self, context, instance, state):
        """Signal to engine service to perform power action on instance."""
        cctxt = self.client.prepare(topic=self.topic, server=CONF.host)
        return cctxt.cast(context, 'set_power_state',
                          instance=instance, state=state)

    def rebuild_instance(self, context, instance):
        """Signal to engine service to rebuild an instance."""
        cctxt = self.client.prepare(topic=self.topic, server=CONF.host)
        return cctxt.cast(context, 'rebuild_instance', instance=instance)

    def get_serial_console(self, context, instance):
        cctxt = self.client.prepare(topic=self.topic, server=CONF.host)
        return cctxt.call(context, 'get_serial_console',
                          instance=instance)
