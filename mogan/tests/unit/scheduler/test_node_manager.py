# Copyright (c) 2016 OpenStack Foundation
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
"""
Tests For NodeManager
"""

import mock
from oslo_context import context
from oslo_versionedobjects import base as object_base

from mogan.common import exception
from mogan.objects import compute_port
from mogan.scheduler import filters
from mogan.scheduler import node_manager
from mogan.scheduler.node_manager import NodeState
from mogan.tests import base as test
from mogan.tests.unit.objects import utils as obj_utils


class FakeFilterClass1(filters.BaseNodeFilter):
    def node_passes(self, node_state, filter_properties):
        pass


class FakeFilterClass2(filters.BaseNodeFilter):
    def node_passes(self, node_state, filter_properties):
        pass


class NodeManagerTestCase(test.TestCase):
    """Test case for NodeManager class."""

    def setUp(self):
        super(NodeManagerTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.node_manager = node_manager.NodeManager()

        fake_node = obj_utils.get_test_compute_node(self.ctxt)
        fake_ports = object_base.obj_make_list(
            self.ctxt, compute_port.ComputePortList(self.ctxt),
            compute_port.ComputePort, [])
        fake_node.ports = fake_ports
        self.fake_nodes = [NodeState(fake_node)]

    def test_choose_node_filters_not_found(self):
        self.override_config('scheduler_default_filters', 'FakeFilterClass3',
                             'scheduler')
        self.node_manager.filter_classes = [FakeFilterClass1,
                                            FakeFilterClass2]
        self.assertRaises(exception.SchedulerNodeFilterNotFound,
                          self.node_manager._choose_node_filters, None)

    def test_choose_node_filters(self):
        self.override_config('scheduler_default_filters', 'FakeFilterClass2',
                             group='scheduler')
        self.node_manager.filter_classes = [FakeFilterClass1,
                                            FakeFilterClass2]

        # Test returns 1 correct filter class
        filter_classes = self.node_manager._choose_node_filters(None)
        self.assertEqual(1, len(filter_classes))
        self.assertEqual('FakeFilterClass2', filter_classes[0].__name__)

    @mock.patch('mogan.scheduler.node_manager.NodeManager.'
                '_choose_node_filters')
    def test_get_filtered_nodes(self, _mock_choose_node_filters):
        filter_class = FakeFilterClass1
        mock_func = mock.Mock()
        mock_func.return_value = True
        filter_class._filter_one = mock_func
        _mock_choose_node_filters.return_value = [filter_class]

        fake_properties = {'moo': 1, 'cow': 2}
        expected = []
        for fake_node in self.fake_nodes:
            expected.append(mock.call(fake_node, fake_properties))

        result = self.node_manager.get_filtered_nodes(self.fake_nodes,
                                                      fake_properties)
        self.assertEqual(expected, mock_func.call_args_list)
        self.assertEqual(set(self.fake_nodes), set(result))
