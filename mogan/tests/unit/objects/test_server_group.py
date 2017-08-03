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


class TestServerGroupObject(base.DbTestCase):

    def setUp(self):
        super(TestServerGroupObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_db_server_group =utils.get_test_server_group(
            user_id=None, project_id=None)

    def test_get_by_uuid(self):
        uuid = self.fake_db_server_group['uuid']
        with mock.patch.object(self.dbapi, 'server_group_get',
                               autospec=True) as mock_server_group_get:
            mock_server_group_get.return_value = self.fake_db_server_group
            server_group = objects.ServerGroup.get_by_uuid(self.context, uuid)
            mock_server_group_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, server_group._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'server_group_create',
                               autospec=True) as mock_server_group_create:
            mock_server_group_create.return_value = self.fake_db_server_group
            server_group = objects.ServerGroup(self.context,
                                               **self.fake_db_server_group)
            values = server_group.obj_get_changes()
            policies = values.pop('policies', None)
            members = values.pop('members', None)
            server_group.create()
            mock_server_group_create.assert_called_once_with(
                self.context, values, policies=policies, members=members)
            self.assertEqual(self.fake_db_server_group['uuid'],
                             server_group['uuid'])

    def test_delete(self):
        sg_uuid = self.fake_db_server_group['uuid']
        with mock.patch.object(self.dbapi, 'server_group_delete',
                               autospec=True) as mock_server_group_delete:
            server_group = objects.ServerGroup(self.context,
                                               **self.fake_db_server_group)
            server_group.destroy()
            mock_server_group_delete.assert_called_once_with(
                self.context, sg_uuid)

    def test_save(self):
        sg_uuid = self.fake_db_server_group['uuid']
        with mock.patch.object(self.dbapi, 'server_group_update',
                               autospec=True) as mock_server_group_update:
            server_group = objects.ServerGroup(self.context,
                                               **self.fake_db_server_group)
            server_group.name = 'new_sg'
            updates = server_group.obj_get_changes()
            server_group.save(self.context)
            mock_server_group_update.return_value = self.fake_db_server_group
            mock_server_group_update.assert_called_once_with(
                self.context, sg_uuid, updates)
