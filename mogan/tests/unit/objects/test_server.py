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


class TestServerObject(base.DbTestCase):

    def setUp(self):
        super(TestServerObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_server = utils.get_test_server(context=self.ctxt)
        self.server = obj_utils.get_test_server(
            self.ctxt, **self.fake_server)

    def test_get(self):
        uuid = self.fake_server['uuid']
        with mock.patch.object(self.dbapi, 'server_get',
                               autospec=True) as mock_server_get:
            mock_server_get.return_value = self.fake_server

            server = objects.Server.get(self.context, uuid)

            mock_server_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, server._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'server_get_all',
                               autospec=True) as mock_server_get_all:
            mock_server_get_all.return_value = [self.fake_server]

            project_only = False
            servers = objects.Server.list(self.context, project_only)

            mock_server_get_all.assert_called_once_with(
                self.context, project_only)
            self.assertIsServer(servers[0], objects.Server)
            self.assertEqual(self.context, servers[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'server_create',
                               autospec=True) as mock_server_create:
            mock_server_create.return_value = self.fake_server
            server = objects.Server(self.context, **self.fake_server)
            server.obj_get_changes()
            server.create(self.context)
            expected_called = copy.deepcopy(self.fake_server)
            expected_called['nics'][0].update(
                server_uuid=self.fake_server['uuid'])
            mock_server_create.assert_called_once_with(self.context,
                                                         expected_called)
            self.assertEqual(self.fake_server['uuid'], server['uuid'])

    def test_destroy(self):
        uuid = self.fake_server['uuid']
        with mock.patch.object(self.dbapi, 'server_destroy',
                               autospec=True) as mock_server_destroy:
            server = objects.Server(self.context, **self.fake_server)
            server.destroy(self.context)
            mock_server_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_server['uuid']
        with mock.patch.object(self.dbapi, 'server_update',
                               autospec=True) as mock_server_update:
            with mock.patch.object(self.dbapi, 'server_nic_update_or_create',
                                   autospec=True) as mock_server_nic_update:
                mock_server_update.return_value = self.fake_server
                server_nics = self.fake_server['nics']
                port_id = server_nics[0]['port_id']
                server = objects.Server(self.context, **self.fake_server)
                updates = server.obj_get_changes()
                updates.pop('nics', None)
                server.save(self.context)
                mock_server_update.assert_called_once_with(
                    self.context, uuid, updates)
                expected_called_nic = copy.deepcopy(server_nics[0])
                expected_called_nic.update(server_uuid=uuid)
                mock_server_nic_update.assert_called_once_with(
                    self.context, port_id, expected_called_nic)

    def test_save_after_refresh(self):
        db_server = utils.create_test_server(context=self.ctxt)
        server = objects.Server.get(self.context, db_server.uuid)
        server.refresh(self.context)
        server.name = 'refresh'
        server.save(self.context)
