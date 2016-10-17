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
from nimble.tests import base as test
from nimble.tests.unit.engine.scheduler import fakes


class FilterSchedulerTestCase(test.TestCase):
    """Test case for Filter Scheduler."""
    def setUp(self):
        super(FilterSchedulerTestCase, self).setUp()
        self.node_cache = []
        self.node_cache.append(fakes.fakenode1)
        self.node_cache.append(fakes.fakenode2)
        self.node_cache.append(fakes.fakenode3)

    def test_create_instance_no_nodes(self):
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')
        request_spec = {
            'instance_id': 'fa617131-cdbc-45dc-afff-f21f17ae054e',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='faketype'),
        }

        validhost = sched.schedule(fake_context, request_spec, {})
        self.assertIsNone(validhost)

    def test_create_instance_no_nodes_invalid_req(self):
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')

        # request_spec is missing 'instance_properties'
        request_spec = {
            'instance_type': dict(name='type1'),
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
            'instance_id': 'fa617131-cdbc-45dc-afff-f21f17ae054e',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
        }

        self.assertRaises(exception.NoValidNode,
                          sched.schedule,
                          fake_context,
                          request_spec,
                          {})

    def test_schedule_happy_day(self):
        # Make sure there's nothing glaringly wrong with _schedule()
        # by doing a happy day pass through.
        sched = fakes.FakeFilterScheduler()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)

        request_spec = {
            'instance_id': 'fa617131-cdbc-45dc-afff-f21f17ae054e',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='type1'),
        }

        weighed_node = sched.schedule(fake_context, request_spec,
                                      self.node_cache, {})
        self.assertIsNotNone(weighed_node.obj)

    def test_max_attempts(self):
        self.override_config('scheduler_max_attempts', 4, 'scheduler')

        sched = fakes.FakeFilterScheduler()
        self.assertEqual(4, sched._max_attempts())

    def test_invalid_max_attempts(self):
        self.override_config('scheduler_max_attempts', 0, 'scheduler')

        self.assertRaises(exception.InvalidParameterValue,
                          fakes.FakeFilterScheduler)

    def test_retry_disabled(self):
        # Retry info should not get populated when re-scheduling is off.
        self.override_config('scheduler_max_attempts', 1, 'scheduler')
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_id': 'fa617131-cdbc-45dc-afff-f21f17ae054e',
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='type1'),
        }
        filter_properties = {}

        sched.schedule(self.context, request_spec, '',
                       filter_properties=filter_properties)

        # Should not have retry info in the populated filter properties.
        self.assertNotIn("retry", filter_properties)

    def test_retry_attempt_one(self):
        # Test retry logic on initial scheduling attempt.
        self.override_config('scheduler_max_attempts', 2, 'scheduler')
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='type1'),
        }
        filter_properties = {}

        sched.schedule(self.context, request_spec, '',
                       filter_properties=filter_properties)

        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(1, num_attempts)

    def test_retry_attempt_two(self):
        # Test retry logic when re-scheduling.
        self.override_config('scheduler_max_attempts', 2, 'scheduler')
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='type1'),
        }

        retry = dict(num_attempts=1)
        filter_properties = dict(retry=retry)

        sched.schedule(self.context, request_spec, '',
                       filter_properties=filter_properties)

        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(2, num_attempts)

    def test_retry_exceeded_max_attempts(self):
        # Test for necessary explosion when max retries is exceeded.
        self.override_config('scheduler_max_attempts', 2, 'scheduler')
        sched = fakes.FakeFilterScheduler()

        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'dc613431-cabc-46dc-adddf-f21f17ae358a',
            },
            'instance_type': dict(name='type1'),
        }

        retry = dict(num_attempts=2)
        filter_properties = dict(retry=retry)

        self.assertRaises(exception.NoValidNode, sched.schedule, self.context,
                          request_spec, '',
                          filter_properties=filter_properties)

    def test_add_retry_node(self):
        retry = dict(num_attempts=1, nodes=[])
        filter_properties = dict(retry=retry)
        node = "fakenode"

        sched = fakes.FakeFilterScheduler()
        sched._add_retry_node(filter_properties, node)

        nodes = filter_properties['retry']['nodes']
        self.assertEqual(1, len(nodes))
        self.assertEqual(node, nodes[0])
