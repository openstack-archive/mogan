# Copyright 2017 Huawei Technologies Co.,LTD.
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

import copy

import mock
from oslo_context import context

from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils
from mogan.tests.unit.objects import utils as obj_utils


class TestComputePortObject(base.DbTestCase):

    def setUp(self):
        super(TestComputePortObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_port = utils.get_test_compute_port(context=self.ctxt)
        self.port = obj_utils.get_test_compute_port(
            self.ctxt, **self.fake_port)

    def test_get(self):
        port_uuid = self.fake_port['port_uuid']
        with mock.patch.object(self.dbapi, 'compute_port_get',
                               autospec=True) as mock_port_get:
            mock_port_get.return_value = self.fake_port

            port = objects.ComputePort.get(self.context, port_uuid)

            mock_port_get.assert_called_once_with(self.context, port_uuid)
            self.assertEqual(self.context, port._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'compute_port_get_all',
                               autospec=True) as mock_port_get_all:
            mock_port_get_all.return_value = [self.fake_port]

            ports = objects.ComputePort.list(self.context)

            mock_port_get_all.assert_called_once_with(self.context)
            self.assertIsInstance(ports[0], objects.ComputePort)
            self.assertEqual(self.context, ports[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'compute_port_create',
                               autospec=True) as mock_port_create:
            mock_port_create.return_value = self.fake_port
            port = objects.ComputePort(self.context, **self.fake_port)
            port.obj_get_changes()
            port.create(self.context)
            expected_called = copy.deepcopy(self.fake_port)
            mock_port_create.assert_called_once_with(self.context,
                                                     expected_called)
            self.assertEqual(self.fake_port['port_uuid'], port['port_uuid'])

    def test_destroy(self):
        uuid = self.fake_port['port_uuid']
        with mock.patch.object(self.dbapi, 'compute_port_destroy',
                               autospec=True) as mock_port_destroy:
            port = objects.ComputePort(self.context, **self.fake_port)
            port.destroy(self.context)
            mock_port_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_port['port_uuid']
        with mock.patch.object(self.dbapi, 'compute_port_update',
                               autospec=True) as mock_port_update:
            mock_port_update.return_value = self.fake_port
            port = objects.ComputePort(self.context, **self.fake_port)
            updates = port.obj_get_changes()
            port.save(self.context)
            mock_port_update.assert_called_once_with(
                self.context, uuid, updates)

    def test_save_after_refresh(self):
        db_port = utils.create_test_compute_port(context=self.ctxt)
        port = objects.ComputePort.get(self.context, db_port.port_uuid)
        port.refresh(self.context)
        port.port_type = 'refresh'
        port.save(self.context)
