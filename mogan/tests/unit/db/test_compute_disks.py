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

"""Tests for manipulating ComputeDisks via the DB API"""

from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbComputeDiskTestCase(base.DbTestCase):

    def test_compute_disk_create(self):
        utils.create_test_compute_disk()

    def test_compute_disk_create_with_same_uuid(self):
        utils.create_test_compute_disk(disk_uuid='uuid')
        self.assertRaises(exception.ComputeDiskAlreadyExists,
                          utils.create_test_compute_disk,
                          disk_uuid='uuid')

    def test_compute_disk_get_by_uuid(self):
        disk = utils.create_test_compute_disk()
        res = self.dbapi.compute_disk_get(self.context, disk.disk_uuid)
        self.assertEqual(disk.disk_uuid, res.disk_uuid)

    def test_compute_disk_get_not_exist(self):
        self.assertRaises(exception.ComputeDiskNotFound,
                          self.dbapi.compute_disk_get,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_disk_get_all(self):
        disk_uuids = []
        for i in range(0, 3):
            disk = utils.create_test_compute_disk(
                disk_uuid=uuidutils.generate_uuid())
            disk_uuids.append(six.text_type(disk['disk_uuid']))

        res = self.dbapi.compute_disk_get_all(self.context)
        res_uuids = [r.disk_uuid for r in res]
        self.assertItemsEqual(disk_uuids, res_uuids)

    def test_compute_disk_destroy(self):
        disk = utils.create_test_compute_disk()
        self.dbapi.compute_disk_destroy(self.context, disk.disk_uuid)
        self.assertRaises(exception.ComputeDiskNotFound,
                          self.dbapi.compute_disk_get,
                          self.context,
                          disk.disk_uuid)

    def test_compute_disk_destroy_not_exist(self):
        self.assertRaises(exception.ComputeDiskNotFound,
                          self.dbapi.compute_disk_destroy,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_disk_update(self):
        disk = utils.create_test_compute_disk()
        res = self.dbapi.compute_disk_update(self.context,
                                             disk.disk_uuid,
                                             {'disk_type': 'foo'})
        self.assertEqual('foo', res.disk_type)
