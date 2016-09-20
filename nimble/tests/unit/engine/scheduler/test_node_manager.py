# Copyright (c) 2011 OpenStack Foundation
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

from nimble.common import exception
from nimble.engine.scheduler import filters
from nimble.engine.scheduler import node_manager
from nimble.engine.scheduler.node_manager import NodeState
from nimble.tests import base as test
from ironic.objects import node as ironic_node

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
        self.node_manager = node_manager.NodeManager()
        node1 = ironic_node()
        node1['uuid'] = '12345757'
        node1['capabilities'] = ''
        node1['availability_zone'] = 'az1'
        node1['instance_type'] = 'type1'

        node2 = ironic_node()
        node2['uuid'] = '12345757sdf'
        node2['capabilities'] = ''
        node2['availability_zone'] = 'az2'
        node2['instance_type'] = 'type2'

        node3 = ironic_node()
        node3['uuid'] = '12345757sdf'
        node3['capabilities'] = ''
        node3['availability_zone'] = 'az3'
        node3['instance_type'] = 'type3'

        self.fake_nodes = [NodeState(node1), NodeState(node1), NodeState(node1)]

    def test_choose_node_filters_not_found(self):
        self.flags(scheduler_default_filters='FakeFilterClass3')
        self.node_manager.filter_classes = [FakeFilterClass1,
                                            FakeFilterClass2]
        self.assertRaises(exception.SchedulerNodeFilterNotFound,
                          self.node_manager._choose_node_filters, None)

    def test_choose_node_filters(self):
        self.flags(scheduler_default_filters=['FakeFilterClass2'])
        self.node_manager.filter_classes = [FakeFilterClass1,
                                            FakeFilterClass2]

        # Test 'volume' returns 1 correct function
        filter_classes = self.node_manager._choose_node_filters(None)
        self.assertEqual(1, len(filter_classes))
        self.assertEqual('FakeFilterClass2', filter_classes[0].__name__)

    @mock.patch('nimble.engine.scheduler.node_manager.NodeManager.'
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
