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

"""Tests for manipulating ComputePorts via the DB API"""

from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbComputePortTestCase(base.DbTestCase):

    def test_compute_port_create(self):
        utils.create_test_compute_port()

    def test_compute_port_create_with_same_uuid(self):
        utils.create_test_compute_port(port_uuid='uuid')
        self.assertRaises(exception.ComputePortAlreadyExists,
                          utils.create_test_compute_port,
                          port_uuid='uuid')

    def test_compute_port_get_by_uuid(self):
        port = utils.create_test_compute_port()
        res = self.dbapi.compute_port_get(self.context, port.port_uuid)
        self.assertEqual(port.port_uuid, res.port_uuid)

    def test_compute_port_get_not_exist(self):
        self.assertRaises(exception.ComputePortNotFound,
                          self.dbapi.compute_port_get,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_port_get_all(self):
        port_uuids = []
        for i in range(0, 3):
            port = utils.create_test_compute_port(
                port_uuid=uuidutils.generate_uuid())
            port_uuids.append(six.text_type(port['port_uuid']))

        res = self.dbapi.compute_port_get_all(self.context)
        res_uuids = [r.port_uuid for r in res]
        self.assertItemsEqual(port_uuids, res_uuids)

    def test_compute_port_destroy(self):
        port = utils.create_test_compute_port()
        self.dbapi.compute_port_destroy(self.context, port.port_uuid)
        self.assertRaises(exception.ComputePortNotFound,
                          self.dbapi.compute_port_get,
                          self.context,
                          port.port_uuid)

    def test_compute_port_destroy_not_exist(self):
        self.assertRaises(exception.ComputePortNotFound,
                          self.dbapi.compute_port_destroy,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_port_update(self):
        port = utils.create_test_compute_port()
        res = self.dbapi.compute_port_update(self.context,
                                             port.port_uuid,
                                             {'address': 'aa:bb:cc:dd:ee:ff'})
        self.assertEqual('aa:bb:cc:dd:ee:ff', res.address)
