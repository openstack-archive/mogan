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

from nimble.common import context
from nimble.common import exception
from nimble import objects
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils


class TestInstanceTypeObject(base.DbTestCase):

    def setUp(self):
        super(TestInstanceTypeObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_type = utils.get_test_instance_type(context=self.ctxt)
        self.fake_type['extra_specs'] = {}

    def test_get(self):
        uuid = self.fake_type['uuid']
        with mock.patch.object(self.dbapi, 'instance_type_get',
                               autospec=True) as mock_type_get:
            mock_type_get.return_value = self.fake_type

            instance_type = objects.InstanceType.get(self.context, uuid)

            mock_type_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, instance_type._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'instance_type_get_all',
                               autospec=True) as mock_type_get_all:
            mock_type_get_all.return_value = [self.fake_type]

            types = objects.InstanceType.list(self.context)

            mock_type_get_all.assert_called_once_with(self.context)
            self.assertIsInstance(types[0], objects.InstanceType)
            self.assertEqual(self.context, types[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'instance_type_create',
                               autospec=True) as mock_type_create:
            mock_type_create.return_value = self.fake_type
            instance_type = objects.InstanceType(self.context,
                                                 **self.fake_type)
            values = instance_type.obj_get_changes()
            instance_type.create(self.context)
            mock_type_create.assert_called_once_with(self.context, values)
            self.assertEqual(self.fake_type['id'], instance_type['id'])

    def test_destroy(self):
        uuid = self.fake_type['uuid']
        with mock.patch.object(self.dbapi, 'instance_type_destroy',
                               autospec=True) as mock_type_destroy:
            mock_type_destroy.return_value = self.fake_type
            instance_type = objects.InstanceType(self.context,
                                                 **self.fake_type)
            instance_type.destroy(self.context)
            mock_type_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        instance_type = objects.InstanceType(self.context,
                                             **self.fake_type)
        self.assertRaises(exception.ObjectActionError,
                          instance_type.save,
                          self.context)
