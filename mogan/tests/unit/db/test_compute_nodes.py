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

"""Tests for manipulating ComputeNodes via the DB API"""

from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbComputeNodeTestCase(base.DbTestCase):

    def test_compute_node_create(self):
        utils.create_test_compute_node()

    def test_compute_node_create_with_same_uuid(self):
        utils.create_test_compute_node(node_uuid='uuid')
        self.assertRaises(exception.ComputeNodeAlreadyExists,
                          utils.create_test_compute_node,
                          node_uuid='uuid')

    def test_compute_node_get_by_uuid(self):
        node = utils.create_test_compute_node()
        res = self.dbapi.compute_node_get(self.context, node.node_uuid)
        self.assertEqual(node.node_uuid, res.node_uuid)

    def test_compute_node_get_not_exist(self):
        self.assertRaises(exception.ComputeNodeNotFound,
                          self.dbapi.compute_node_get,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_node_get_all(self):
        node_uuids = []
        for i in range(0, 3):
            node = utils.create_test_compute_node(
                node_uuid=uuidutils.generate_uuid())
            node_uuids.append(six.text_type(node['node_uuid']))

        res = self.dbapi.compute_node_get_all(self.context)
        res_uuids = [r.node_uuid for r in res]
        for node_uuid in node_uuids:
            self.assertIn(node_uuid, res_uuids)

    def test_compute_node_destroy(self):
        node = utils.create_test_compute_node()
        self.dbapi.compute_node_destroy(self.context, node.node_uuid)
        self.assertRaises(exception.ComputeNodeNotFound,
                          self.dbapi.compute_node_get,
                          self.context,
                          node.node_uuid)

    def test_compute_node_destroy_not_exist(self):
        self.assertRaises(exception.ComputeNodeNotFound,
                          self.dbapi.compute_node_destroy,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_compute_node_update(self):
        node = utils.create_test_compute_node()
        res = self.dbapi.compute_node_update(self.context,
                                             node.node_uuid,
                                             {'hypervisor_type': 'foo'})
        self.assertEqual('foo', res.hypervisor_type)
