# Copyright 2017 Intel
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


import mock
from oslo_context import context
from oslo_utils import uuidutils

from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.objects import utils as obj_utils


class TestInstanceFaultObject(base.DbTestCase):

    def setUp(self):
        super(TestInstanceFaultObject, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_create(self):
        with mock.patch.object(self.dbapi, 'instance_fault_create',
                               autospec=True) as mock_fault_create:
            uuid = uuidutils.generate_uuid()
            fake_fault = obj_utils.get_test_instance_fault(instance_uuid=uuid)
            mock_fault_create.return_value = fake_fault
            instance_fault = objects.InstanceFault(self.ctxt)
            instance_fault.instance_uuid = uuid
            instance_fault.code = 456
            instance_fault.message = 'foo'
            instance_fault.detail = 'you screwed up'
            instance_fault.create()
            self.assertEqual(123456, instance_fault.id)
            mock_fault_create.assert_called_once_with(
                self.ctxt,
                {'instance_uuid': uuid,
                 'code': 456,
                 'message': 'foo',
                 'detail': 'you screwed up'})

    def test_get_latest_for_instance(self):
        with mock.patch.object(self.dbapi,
                               'instance_fault_get_by_instance_uuids',
                               autospec=True) as mock_fault_get:
            uuid = uuidutils.generate_uuid()
            fake_faults = obj_utils.get_test_instance_faults(
                instance_uuid=uuid)
            mock_fault_get.return_value = fake_faults
            instance_fault = objects.InstanceFault.get_latest_for_instance(
                self.ctxt, 'fake-uuid')
            for key in fake_faults['fake-uuid'][0]:
                self.assertEqual(fake_faults['fake-uuid'][0][key],
                                 instance_fault[key])
            mock_fault_get.assert_called_once_with(self.ctxt, ['fake-uuid'])
