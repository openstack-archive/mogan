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
from oslo_utils import uuidutils

from nimble.common import context
from nimble.engine.flows import create_instance
from nimble.engine.scheduler import filter_scheduler as scheduler
from nimble.tests import base
from nimble.tests.unit.objects import utils as obj_utils


class CreateInstanceFlowTestCase(base.TestCase):

    def setUp(self):
        super(CreateInstanceFlowTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    @mock.patch.object(scheduler.FilterScheduler, 'schedule')
    def test_schedule_task_execute(self, mock_schedule):
        fake_uuid = uuidutils.generate_uuid()
        fake_engine_manager = mock.MagicMock()
        fake_request_spec = mock.MagicMock()
        fake_filter_props = mock.MagicMock()
        fake_engine_manager.scheduler = scheduler.FilterScheduler()
        task = create_instance.ScheduleCreateInstanceTask(
            fake_engine_manager)
        instance_obj = obj_utils.get_test_instance(self.ctxt)
        mock_schedule.return_value = fake_uuid

        task.execute(self.ctxt,
                     instance_obj,
                     fake_request_spec,
                     fake_filter_props)
        mock_schedule.assert_called_once_with(self.ctxt,
                                              fake_request_spec,
                                              fake_engine_manager.node_cache,
                                              fake_filter_props)
        self.assertEqual(fake_uuid, instance_obj.node_uuid)

    def test_schedule_task_revert(self):
        fake_engine_manager = mock.MagicMock()
        fake_result = mock.MagicMock()
        fake_flow_failures = mock.MagicMock()
        task = create_instance.ScheduleCreateInstanceTask(
            fake_engine_manager)
        instance_obj = obj_utils.get_test_instance(self.ctxt)

        self.assertIsNotNone(instance_obj.node_uuid)
        task.revert(self.ctxt,
                    fake_result,
                    fake_flow_failures,
                    instance_obj)
        self.assertIsNone(instance_obj.node_uuid)
