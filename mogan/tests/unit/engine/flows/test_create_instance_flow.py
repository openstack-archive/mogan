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
""" Tests for create_instance TaskFlow """

import mock
from oslo_context import context
from oslo_utils import uuidutils

from mogan.engine.baremetal.ironic import IronicDriver
from mogan.engine.flows import create_instance
from mogan.engine import manager
from mogan.engine.scheduler import filter_scheduler as scheduler
from mogan import objects
from mogan.tests import base
from mogan.tests.unit.objects import utils as obj_utils


class CreateInstanceFlowTestCase(base.TestCase):

    def setUp(self):
        super(CreateInstanceFlowTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    @mock.patch.object(objects.instance.Instance, 'save')
    @mock.patch.object(scheduler.FilterScheduler, 'schedule')
    def test_schedule_task_execute(self, mock_schedule, mock_save):
        fake_uuid = uuidutils.generate_uuid()
        fake_engine_manager = mock.MagicMock()
        fake_request_spec = mock.MagicMock()
        fake_filter_props = mock.MagicMock()
        fake_engine_manager.scheduler = scheduler.FilterScheduler()
        task = create_instance.ScheduleCreateInstanceTask(
            fake_engine_manager)
        instance_obj = obj_utils.get_test_instance(self.ctxt)
        mock_schedule.return_value = fake_uuid
        mock_save.side_effect = None

        task.execute(self.ctxt,
                     instance_obj,
                     fake_request_spec,
                     fake_filter_props)
        mock_schedule.assert_called_once_with(self.ctxt,
                                              fake_request_spec,
                                              fake_filter_props)
        self.assertEqual(fake_uuid, instance_obj.node_uuid)

    @mock.patch.object(objects.instance.Instance, 'save')
    @mock.patch.object(create_instance.BuildNetworkTask, '_build_networks')
    def test_create_network_task_execute(self, mock_build_networks, mock_save):
        fake_engine_manager = mock.MagicMock()
        fake_requested_networks = mock.MagicMock()
        task = create_instance.BuildNetworkTask(fake_engine_manager)
        instance_obj = obj_utils.get_test_instance(self.ctxt)
        mock_build_networks.return_value = None
        mock_save.return_value = None

        task.execute(self.ctxt, instance_obj, fake_requested_networks)
        mock_build_networks.assert_called_once_with(self.ctxt,
                                                    instance_obj,
                                                    fake_requested_networks)

    @mock.patch.object(IronicDriver, 'spawn')
    def test_create_instance_task_execute(self, mock_spawn):
        flow_manager = manager.EngineManager('test-host', 'test-topic')
        task = create_instance.CreateInstanceTask(
            flow_manager.driver)
        instance_obj = obj_utils.get_test_instance(self.ctxt)
        mock_spawn.side_effect = None

        task.execute(self.ctxt, instance_obj)
        mock_spawn.assert_called_once_with(self.ctxt, instance_obj)
