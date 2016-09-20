# Copyright 2011 OpenStack Foundation
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
Tests For Filter Scheduler.
"""

from nimble.common import context
from nimble.common import exception
from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import node_manager
from nimble.tests import base as test
from nimble.tests.unit.engine.scheduler import fakes

 
class FilterSchedulerTestCase(test.TestCase):
    """Test case for Filter Scheduler."""

    driver_cls = filter_scheduler.FilterScheduler

    def test_create_instance_no_nodes(self):
        # Ensure empty nodes/child_zones result in NoValidNodes exception.
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')
        request_spec = {
            'instance_id': '123456',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }

        self.assertRaises(exception.NoValidNode, sched.schedule,
                          fake_context, request_spec, {})

    def test_create_instance_no_nodes_invalid_req(self):
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')

        # request_spec is missing 'instance_id'
        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }
        self.assertRaises(exception.NoValidNode,
                          sched.schedule,
                          fake_context,
                          request_spec,
                          {})

    def test_create_instance_no_instance_type(self):
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')

        # request_spec is missing 'instance_type'
        request_spec = {
            'instance_id': '123456',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
        }
        self.assertRaises(exception.NoValidNode,
                          sched.schedule,
                          fake_context,
                          request_spec,
                          {})

    def test_schedule_happy_day(self, _mock_service_get_all):
        # Make sure there's nothing glaringly wrong with _schedule()
        # by doing a happy day pass through.
        sched = fakes.FakeFilterScheduler()
        sched.node_manager = fakes.FakeNodeManager()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)

        fakes.mock_node_manager_db_calls(_mock_service_get_all)

        request_spec = {
            'instance_id': '123456',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }
        weighed_node = sched._schedule(fake_context, request_spec, {})
        self.assertIsNotNone(weighed_node.obj)
        #self.assertTrue(sched.node_manager.
        #get_all_node_states _mock_service_get_all.called)

    def test_max_attempts(self):
        self.flags(scheduler_max_attempts=4)

        sched = fakes.FakeFilterScheduler()
        self.assertEqual(4, sched._max_attempts())

    def test_invalid_max_attempts(self):
        self.flags(scheduler_max_attempts=0)

        self.assertRaises(exception.InvalidParameterValue,
                          fakes.FakeFilterScheduler)

    def test_retry_disabled(self):
        # Retry info should not get populated when re-scheduling is off.
        self.flags(scheduler_max_attempts=1)
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_id': '123456',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }
        filter_properties = {}

        sched._schedule(self.context, request_spec,
                        filter_properties=filter_properties)

        # Should not have retry info in the populated filter properties.
        self.assertNotIn("retry", filter_properties)

    def test_retry_attempt_one(self):
        # Test retry logic on initial scheduling attempt.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }
        filter_properties = {}

        sched._schedule(self.context, request_spec,
                        filter_properties=filter_properties)

        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(1, num_attempts)

    def test_retry_attempt_two(self):
        # Test retry logic when re-scheduling.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }

        retry = dict(num_attempts=1)
        filter_properties = dict(retry=retry)

        sched._schedule(self.context, request_spec,
                        filter_properties=filter_properties)

        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(2, num_attempts)

    def test_retry_exceeded_max_attempts(self):
        # Test for necessary explosion when max retries is exceeded.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }

        retry = dict(num_attempts=2)
        filter_properties = dict(retry=retry)

        self.assertRaises(exception.NoValidNode, sched._schedule, self.context,
                          request_spec, filter_properties=filter_properties)

    def test_add_retry_node(self):
        retry = dict(num_attempts=1, nodes=[])
        filter_properties = dict(retry=retry)
        node = "fakenode"

        sched = fakes.FakeFilterScheduler()
        sched._add_retry_node(filter_properties, node)

        nodes = filter_properties['retry']['nodes']
        self.assertEqual(1, len(nodes))
        self.assertEqual(node, nodes[0])

    def test_post_select_populate(self):
        # Test addition of certain filter props after a node is selected.
        retry = {'nodes': [], 'num_attempts': 1}
        filter_properties = {'retry': retry}
        sched = fakes.FakeFilterScheduler()

        node_state = node_manager.NodeState('node')
        node_state.total_capacity_gb = 1024
        sched._post_select_populate_filter_properties(filter_properties,
                                                      node_state)

        self.assertEqual('node',
                         filter_properties['retry']['nodes'][0])

        self.assertEqual(1024, node_state.total_capacity_gb)

    def _node_passes_filters_setup(self, mock_obj):
        sched = fakes.FakeFilterScheduler()
        sched.node_manager = fakes.FakeNodeManager()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)

        fakes.mock_node_manager_db_calls(mock_obj)

        return (sched, fake_context)
