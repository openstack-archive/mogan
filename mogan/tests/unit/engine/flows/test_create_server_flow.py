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
""" Tests for create_server TaskFlow """

import mock
from oslo_context import context

from mogan.engine.baremetal.ironic import IronicDriver
from mogan.engine.flows import create_server
from mogan.engine import manager
from mogan import objects
from mogan.tests import base
from mogan.tests.unit.objects import utils as obj_utils


class CreateServerFlowTestCase(base.TestCase):

    def setUp(self):
        super(CreateServerFlowTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    @mock.patch.object(objects.server.Server, 'save')
    @mock.patch.object(create_server.BuildNetworkTask, '_build_networks')
    def test_create_network_task_execute(self, mock_build_networks, mock_save):
        fake_engine_manager = mock.MagicMock()
        fake_requested_networks = mock.MagicMock()
        fake_ports = mock.MagicMock()
        task = create_server.BuildNetworkTask(fake_engine_manager)
        server_obj = obj_utils.get_test_server(self.ctxt)
        mock_build_networks.return_value = None
        mock_save.return_value = None

        task.execute(
            self.ctxt, server_obj, fake_requested_networks, fake_ports)
        mock_build_networks.assert_called_once_with(self.ctxt,
                                                    server_obj,
                                                    fake_requested_networks,
                                                    fake_ports)

    @mock.patch.object(IronicDriver, 'spawn')
    def test_create_server_task_execute(self, mock_spawn):
        flow_manager = manager.EngineManager('test-host', 'test-topic')
        task = create_server.CreateServerTask(
            flow_manager.driver)
        server_obj = obj_utils.get_test_server(self.ctxt)
        mock_spawn.side_effect = None

        task.execute(self.ctxt, server_obj, {'value': 'configdrive'})
        mock_spawn.assert_called_once_with(
            self.ctxt, server_obj, 'configdrive')
