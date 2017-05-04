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

from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class TestFlavorObject(base.DbTestCase):

    def setUp(self):
        super(TestFlavorObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_type = utils.get_test_flavor(context=self.ctxt)
        self.fake_type['extra_specs'] = {}

    def test_get(self):
        uuid = self.fake_type['uuid']
        with mock.patch.object(self.dbapi, 'flavor_get',
                               autospec=True) as mock_type_get:
            mock_type_get.return_value = self.fake_type

            flavor = objects.Flavor.get(self.context, uuid)

            mock_type_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, flavor._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'flavor_get_all',
                               autospec=True) as mock_type_get_all:
            mock_type_get_all.return_value = [self.fake_type]

            types = objects.Flavor.list(self.context)

            mock_type_get_all.assert_called_once_with(self.context)
            self.assertIsInstance(types[0], objects.Flavor)
            self.assertEqual(self.context, types[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'flavor_create',
                               autospec=True) as mock_type_create:
            mock_type_create.return_value = self.fake_type
            flavor = objects.Flavor(self.context, **self.fake_type)
            values = flavor.obj_get_changes()
            flavor.create(self.context)
            mock_type_create.assert_called_once_with(self.context, values)
            self.assertEqual(self.fake_type['uuid'], flavor['uuid'])

    def test_destroy(self):
        uuid = self.fake_type['uuid']
        with mock.patch.object(self.dbapi, 'flavor_destroy',
                               autospec=True) as mock_type_destroy:
            mock_type_destroy.return_value = self.fake_type
            flavor = objects.Flavor(self.context, **self.fake_type)
            flavor.destroy(self.context)
            mock_type_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_type['uuid']
        with mock.patch.object(self.dbapi, 'flavor_update',
                               autospec=True) as mock_flavor_update:
            flavor = objects.Flavor(self.context, **self.fake_type)
            flavor.name = 'changed_name'
            updates = flavor.obj_get_changes()
            flavor.save(self.context)
            updates.pop('extra_specs', None)
            updates.pop('cpus', None)
            updates.pop('memory', None)
            updates.pop('disks', None)
            updates.pop('nics', None)
            mock_flavor_update.return_value = self.fake_type
            mock_flavor_update.assert_called_once_with(
                self.context, uuid, updates)
