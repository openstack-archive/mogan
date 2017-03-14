# Copyright 2017 Huawei Technologies Co.,LTD.
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
Client side of the consoleauth RPC API.
"""

from oslo_config import cfg
import oslo_messaging as messaging

from mogan.common import constants
from mogan.common import rpc
from mogan.objects import base as objects_base

CONF = cfg.CONF


class ConsoleAuthAPI(object):
    """Client side of the consoleauth rpc API.

    API version history:

    |    1.0 - Initial version.

    """

    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(ConsoleAuthAPI, self).__init__()
        self.topic = topic
        if self.topic is None:
            self.topic = constants.MANAGER_CONSOLEAUTH_TOPIC

        target = messaging.Target(topic=self.topic,
                                  version='1.0')
        serializer = objects_base.MoganObjectSerializer()
        self.client = rpc.get_client(target,
                                     version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)

    def authorize_console(self, ctxt, token, console_type, host, port,
                          internal_access_path, instance_uuid,
                          access_url):
        # The remote side doesn't return anything, but we want to block
        # until it completes.'
        msg_args = dict(token=token, console_type=console_type,
                        host=host, port=port,
                        internal_access_path=internal_access_path,
                        instance_uuid=instance_uuid,
                        access_url=access_url)

        cctxt = self.client.prepare()
        return cctxt.call(ctxt, 'authorize_console', **msg_args)

    def check_token(self, ctxt, token):
        cctxt = self.client.prepare()
        return cctxt.call(ctxt, 'check_token', token=token)

    def delete_tokens_for_instance(self, ctxt, instance_uuid):
        cctxt = self.client.prepare()
        return cctxt.cast(ctxt,
                          'delete_tokens_for_instance',
                          instance_uuid=instance_uuid)
