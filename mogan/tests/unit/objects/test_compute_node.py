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


class TestComputeNodeObject(base.DbTestCase):

    def setUp(self):
        super(TestComputeNodeObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_node = utils.get_test_compute_node(context=self.ctxt)
        self.node = obj_utils.get_test_compute_node(
            self.ctxt, **self.fake_node)

    def test_get(self):
        node_uuid = self.fake_node['node_uuid']
        with mock.patch.object(self.dbapi, 'compute_node_get',
                               autospec=True) as mock_node_get:
            mock_node_get.return_value = self.fake_node

            node = objects.ComputeNode.get(self.context, node_uuid)

            mock_node_get.assert_called_once_with(self.context, node_uuid)
            self.assertEqual(self.context, node._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'compute_node_get_all',
                               autospec=True) as mock_node_get_all:
            mock_node_get_all.return_value = [self.fake_node]

            nodes = objects.ComputeNode.list(self.context)

            mock_node_get_all.assert_called_once_with(self.context)
            self.assertIsInstance(nodes[0], objects.ComputeNode)
            self.assertEqual(self.context, nodes[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'compute_node_create',
                               autospec=True) as mock_node_create:
            mock_node_create.return_value = self.fake_node
            node = objects.ComputeNode(self.context, **self.fake_node)
            node.obj_get_changes()
            node.create(self.context)
            expected_called = copy.deepcopy(self.fake_node)
            mock_node_create.assert_called_once_with(self.context,
                                                     expected_called)
            self.assertEqual(self.fake_node['node_uuid'], node['node_uuid'])

    def test_destroy(self):
        uuid = self.fake_node['node_uuid']
        with mock.patch.object(self.dbapi, 'compute_node_destroy',
                               autospec=True) as mock_node_destroy:
            node = objects.ComputeNode(self.context, **self.fake_node)
            node.destroy(self.context)
            mock_node_destroy.assert_called_once_with(self.context, uuid)

    def test_save(self):
        uuid = self.fake_node['node_uuid']
        with mock.patch.object(self.dbapi, 'compute_node_update',
                               autospec=True) as mock_node_update:
            mock_node_update.return_value = self.fake_node
            node = objects.ComputeNode(self.context, **self.fake_node)
            updates = node.obj_get_changes()
            node.save(self.context)
            mock_node_update.assert_called_once_with(
                self.context, uuid, updates)

    def test_save_after_refresh(self):
        db_node = utils.create_test_compute_node(context=self.ctxt)
        node = objects.ComputeNode.get(self.context, db_node.node_uuid)
        node.refresh(self.context)
        node.hypervisor_type = 'refresh'
        node.save(self.context)
