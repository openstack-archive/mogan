# coding=utf-8
#
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
import copy

import mock
from oslo_context import context

from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils
from mogan.tests.unit.objects import utils as obj_utils


class TestInstanceObject(base.DbTestCase):

    def setUp(self):
        super(TestInstanceObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_instance = utils.get_test_instance(context=self.ctxt)
        self.instance = obj_utils.get_test_instance(
            self.ctxt, **self.fake_instance)

    def test_get(self):
        uuid = self.fake_instance['uuid']
        with mock.patch.object(self.dbapi, 'instance_get',
                               autospec=True) as mock_instance_get:
            mock_instance_get.return_value = self.fake_instance

            instance = objects.Instance.get(self.context, uuid)

            mock_instance_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, instance._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'instance_get_all',
                               autospec=True) as mock_instance_get_all:
            mock_instance_get_all.return_value = [self.fake_instance]

            project_only = False
            instances = objects.Instance.list(self.context, project_only)

            mock_instance_get_all.assert_called_once_with(
                self.context, project_only)
            self.assertIsInstance(instances[0], objects.Instance)
            self.assertEqual(self.context, instances[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'instance_create',
                               autospec=True) as mock_instance_create:
            mock_instance_create.return_value = self.fake_instance
            instance = objects.Instance(self.context, **self.fake_instance)
            instance.obj_get_changes()
            instance.create(self.context)
            expected_called = copy.deepcopy(self.fake_instance)
            expected_called['nics'][0].update(
                instance_uuid=self.fake_instance['uuid'])
            mock_instance_create.assert_called_once_with(self.context,
                                                         expected_called)
            self.assertEqual(self.fake_instance['uuid'], instance['uuid'])

    def test_destroy(self):
        uuid = self.fake_instance['uuid']
        with mock.patch.object(self.dbapi, 'instance_destroy',
                               autospec=True) as mock_instance_destroy:
            instance = objects.Instance(self.context, **self.fake_instance)
            instance.destroy(self.context)
            mock_instance_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_instance['uuid']
        with mock.patch.object(self.dbapi, 'instance_update',
                               autospec=True) as mock_instance_update:
            with mock.patch.object(self.dbapi, 'instance_nic_update_or_create',
                                   autospec=True) as mock_instance_nic_update:
                mock_instance_update.return_value = self.fake_instance
                instance_nics = self.fake_instance['nics']
                port_id = instance_nics[0]['port_id']
                instance = objects.Instance(self.context, **self.fake_instance)
                updates = instance.obj_get_changes()
                updates.pop('nics', None)
                instance.save(self.context)
                mock_instance_update.assert_called_once_with(
                    self.context, uuid, updates)
                expected_called_nic = copy.deepcopy(instance_nics[0])
                expected_called_nic.update(instance_uuid=uuid)
                mock_instance_nic_update.assert_called_once_with(
                    self.context, port_id, expected_called_nic)

    def test_save_after_refresh(self):
        db_instance = utils.create_test_instance(context=self.ctxt)
        instance = objects.Instance.get(self.context, db_instance.uuid)
        instance.refresh(self.context)
        instance.name = 'refresh'
        instance.save(self.context)
