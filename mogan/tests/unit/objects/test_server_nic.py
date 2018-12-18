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


class TestServerNicObject(base.DbTestCase):

    def setUp(self):
        super(TestServerNicObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_db_server_nic = utils.get_test_server_nic(
            user_id=None, project_id=None)

    def test_get_by_port_id(self):
        port_id = self.fake_db_server_nic['port_id']
        with mock.patch.object(self.dbapi, 'server_nic_get',
                               autospec=True) as mock_server_nic_get:
            mock_server_nic_get.return_value = self.fake_db_server_nic
            server_nic = objects.ServerNic.get_by_port_id(self.context,
                                                          port_id)
            mock_server_nic_get.assert_called_once_with(self.context, port_id)
            self.assertEqual(port_id, server_nic['port_id'])

    def test_create(self):
        port_id = self.fake_db_server_nic['port_id']
        with mock.patch.object(self.dbapi, 'server_nic_update_or_create',
                               autospec=True) as mock_server_nic_create:
            mock_server_nic_create.return_value = self.fake_db_server_nic
            server_nic = objects.ServerNic(self.context,
                                           **self.fake_db_server_nic)
            values = server_nic.obj_get_changes()
            server_nic.create(self.context)
            mock_server_nic_create.assert_called_once_with(
                self.context, port_id, values)
            self.assertEqual(port_id, server_nic['port_id'])

    def test_delete(self):
        port_id = self.fake_db_server_nic['port_id']
        with mock.patch.object(self.dbapi, 'server_nic_delete',
                               autospec=True) as mock_server_nic_delete:
            server_nic = objects.ServerNic(self.context,
                                           **self.fake_db_server_nic)
            server_nic.delete(self.context)
            mock_server_nic_delete.assert_called_once_with(
                self.context, port_id)

    def test_save(self):
        port_id = self.fake_db_server_nic['port_id']
        with mock.patch.object(self.dbapi, 'server_nic_update_or_create',
                               autospec=True) as mock_server_nic_update:
            server_nic = objects.ServerNic(self.context,
                                           **self.fake_db_server_nic)
            server_nic.server_uuid = '123'
            updates = server_nic.obj_get_changes()
            server_nic.save(self.context)
            mock_server_nic_update.return_value = self.fake_db_server_nic
            mock_server_nic_update.assert_called_once_with(
                self.context, port_id, updates)
