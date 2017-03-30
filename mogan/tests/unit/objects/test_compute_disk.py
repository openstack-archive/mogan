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


class TestComputeDiskObject(base.DbTestCase):

    def setUp(self):
        super(TestComputeDiskObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_disk = utils.get_test_compute_disk(context=self.ctxt)
        self.disk = obj_utils.get_test_compute_disk(
            self.ctxt, **self.fake_disk)

    def test_get(self):
        disk_uuid = self.fake_disk['disk_uuid']
        with mock.patch.object(self.dbapi, 'compute_disk_get',
                               autospec=True) as mock_disk_get:
            mock_disk_get.return_value = self.fake_disk

            disk = objects.ComputeDisk.get(self.context, disk_uuid)

            mock_disk_get.assert_called_once_with(self.context, disk_uuid)
            self.assertEqual(self.context, disk._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'compute_disk_get_all',
                               autospec=True) as mock_disk_get_all:
            mock_disk_get_all.return_value = [self.fake_disk]

            disks = objects.ComputeDisk.list(self.context)

            mock_disk_get_all.assert_called_once_with(self.context)
            self.assertIsInstance(disks[0], objects.ComputeDisk)
            self.assertEqual(self.context, disks[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'compute_disk_create',
                               autospec=True) as mock_disk_create:
            mock_disk_create.return_value = self.fake_disk
            disk = objects.ComputeDisk(self.context, **self.fake_disk)
            disk.obj_get_changes()
            disk.create(self.context)
            expected_called = copy.deepcopy(self.fake_disk)
            mock_disk_create.assert_called_once_with(self.context,
                                                     expected_called)
            self.assertEqual(self.fake_disk['disk_uuid'], disk['disk_uuid'])

    def test_destroy(self):
        uuid = self.fake_disk['disk_uuid']
        with mock.patch.object(self.dbapi, 'compute_disk_destroy',
                               autospec=True) as mock_disk_destroy:
            disk = objects.ComputeDisk(self.context, **self.fake_disk)
            disk.destroy(self.context)
            mock_disk_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_disk['disk_uuid']
        with mock.patch.object(self.dbapi, 'compute_disk_update',
                               autospec=True) as mock_disk_update:
            mock_disk_update.return_value = self.fake_disk
            disk = objects.ComputeDisk(self.context, **self.fake_disk)
            updates = disk.obj_get_changes()
            disk.save(self.context)
            mock_disk_update.assert_called_once_with(
                self.context, uuid, updates)

    def test_save_after_refresh(self):
        db_disk = utils.create_test_compute_disk(context=self.ctxt)
        disk = objects.ComputeDisk.get(self.context, db_disk.disk_uuid)
        disk.refresh(self.context)
        disk.disk_type = 'refresh'
        disk.save(self.context)
