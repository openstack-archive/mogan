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

import mock

from nimble.common import context
from nimble.common import exception
from nimble import objects
from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import node_manager
from nimble.tests.unit import fake_constants as fake
from nimble.tests.unit.scheduler import fakes
from nimble.tests.unit.scheduler import test_scheduler


class FilterSchedulerTestCase(test_scheduler.SchedulerTestCase):
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
                          sched.schedule_create_volume,
                          fake_context,
                          request_spec,
                          {})

    def test_create_instance_no_instance_type(self):
        sched = fakes.FakeFilterScheduler()

        fake_context = context.RequestContext('user', 'project')

        # request_spec is missing 'volume_type'
        request_spec = {
            'instance_properties': {
                'availability_zone': 'az1',
                'instance_type_id': 'type1',
            },
            'instance_type': dict('type1'),
        }
        self.assertRaises(exception.NoValidNode,
                          sched.schedule_create_volume,
                          fake_context,
                          request_spec,
                          {})

    @mock.patch('cinder.scheduler.node_manager.NodeManager.'
                'get_all_node_states')
    def test_create_volume_non_admin(self, _mock_get_all_node_states):
        # Test creating a volume locally using create_volume, passing
        # a non-admin context.  DB actions should work.
        self.was_admin = False

        def fake_get(ctxt):
            # Make sure this is called with admin context, even though
            # we're using user context below.
            self.was_admin = ctxt.is_admin
            return {}

        sched = fakes.FakeFilterScheduler()
        _mock_get_all_node_states.side_effect = fake_get

        fake_context = context.RequestContext('user', 'project')

        request_spec = {'volume_properties': {'project_id': 1,
                                              'size': 1},
                        'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_id': fake.VOLUME_ID}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        self.assertRaises(exception.NoValidNode, sched.schedule_create_volume,
                          fake_context, request_spec, {})
        self.assertTrue(self.was_admin)

    @mock.patch('cinder.db.service_get_all')
    def test_schedule_happy_day(self, _mock_service_get_all):
        # Make sure there's nothing glaringly wrong with _schedule()
        # by doing a happy day pass through.
        sched = fakes.FakeFilterScheduler()
        sched.node_manager = fakes.FakeNodeManager()
        fake_context = context.RequestContext('user', 'project',
                                              is_admin=True)

        fakes.mock_node_manager_db_calls(_mock_service_get_all)

        request_spec = {'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        weighed_node = sched._schedule(fake_context, request_spec, {})
        self.assertIsNotNone(weighed_node.obj)
        self.assertTrue(_mock_service_get_all.called)

    @mock.patch('cinder.db.service_get_all')
    def test_create_volume_clear_node_different_with_group(
            self, _mock_service_get_all):
        # Ensure we clear those nodes whose backend is not same as
        # group's backend.
        sched = fakes.FakeFilterScheduler()
        sched.node_manager = fakes.FakeNodeManager()
        fakes.mock_node_manager_db_calls(_mock_service_get_all)
        fake_context = context.RequestContext('user', 'project')
        request_spec = {'volume_properties': {'project_id': 1,
                                              'size': 1},
                        'volume_type': {'name': 'LVM_iSCSI'},
                        'group_backend': 'node@lvmdriver'}
        weighed_node = sched._schedule(fake_context, request_spec, {})
        self.assertIsNone(weighed_node)

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

        request_spec = {'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        filter_properties = {}

        sched._schedule(self.context, request_spec,
                        filter_properties=filter_properties)

        # Should not have retry info in the populated filter properties.
        self.assertNotIn("retry", filter_properties)

    def test_retry_attempt_one(self):
        # Test retry logic on initial scheduling attempt.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()

        request_spec = {'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        filter_properties = {}

        sched._schedule(self.context, request_spec,
                        filter_properties=filter_properties)

        num_attempts = filter_properties['retry']['num_attempts']
        self.assertEqual(1, num_attempts)

    def test_retry_attempt_two(self):
        # Test retry logic when re-scheduling.
        self.flags(scheduler_max_attempts=2)
        sched = fakes.FakeFilterScheduler()

        request_spec = {'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)

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

        request_spec = {'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)

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

    @mock.patch('cinder.db.service_get_all')
    def test_node_passes_filters_happy_day(self, _mock_service_get_topic):
        """Do a successful pass through of with node_passes_filters()."""
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        ret_node = sched.node_passes_filters(ctx, 'node1#lvm1',
                                             request_spec, {})
        self.assertEqual('node1', utils.extract_node(ret_node.node))
        self.assertTrue(_mock_service_get_topic.called)

    @mock.patch('cinder.db.service_get_all')
    def test_node_passes_filters_default_pool_happy_day(
            self, _mock_service_get_topic):
        """Do a successful pass through of with node_passes_filters()."""
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        ret_node = sched.node_passes_filters(ctx, 'node5#_pool0',
                                             request_spec, {})
        self.assertEqual('node5', utils.extract_node(ret_node.node))
        self.assertTrue(_mock_service_get_topic.called)

    @mock.patch('cinder.db.service_get_all')
    def test_node_passes_filters_no_capacity(self, _mock_service_get_topic):
        """Fail the node due to insufficient capacity."""
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI'},
                        'volume_properties': {'project_id': 1,
                                              'size': 1024}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        self.assertRaises(exception.NoValidNode,
                          sched.node_passes_filters,
                          ctx, 'node1#lvm1', request_spec, {})
        self.assertTrue(_mock_service_get_topic.called)

    @mock.patch('cinder.db.service_get_all')
    def test_retype_policy_never_migrate_pass(self, _mock_service_get_topic):
        # Retype should pass if current node passes filters and
        # policy=never. node4 doesn't have enough space to hold an additional
        # 200GB, but it is already the node of this volume and should not be
        # counted twice.
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        extra_specs = {'volume_backend_name': 'lvm4'}
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI',
                                        'extra_specs': extra_specs},
                        'volume_properties': {'project_id': 1,
                                              'size': 200,
                                              'node': 'node4#lvm4'}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        node_state = sched.find_retype_node(ctx, request_spec,
                                            filter_properties={},
                                            migration_policy='never')
        self.assertEqual('node4', utils.extract_node(node_state.node))

    @mock.patch('cinder.db.service_get_all')
    def test_retype_with_pool_policy_never_migrate_pass(
            self, _mock_service_get_topic):
        # Retype should pass if current node passes filters and
        # policy=never. node4 doesn't have enough space to hold an additional
        # 200GB, but it is already the node of this volume and should not be
        # counted twice.
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        extra_specs = {'volume_backend_name': 'lvm3'}
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI',
                                        'extra_specs': extra_specs},
                        'volume_properties': {'project_id': 1,
                                              'size': 200,
                                              'node': 'node3#lvm3'}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        node_state = sched.find_retype_node(ctx, request_spec,
                                            filter_properties={},
                                            migration_policy='never')
        self.assertEqual('node3#lvm3', node_state.node)

    @mock.patch('cinder.db.service_get_all')
    def test_retype_policy_never_migrate_fail(self, _mock_service_get_topic):
        # Retype should fail if current node doesn't pass filters and
        # policy=never.
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        extra_specs = {'volume_backend_name': 'lvm1'}
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI',
                                        'extra_specs': extra_specs},
                        'volume_properties': {'project_id': 1,
                                              'size': 200,
                                              'node': 'node4'}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        self.assertRaises(exception.NoValidNode, sched.find_retype_node, ctx,
                          request_spec, filter_properties={},
                          migration_policy='never')

    @mock.patch('cinder.db.service_get_all')
    def test_retype_policy_demand_migrate_pass(self, _mock_service_get_topic):
        # Retype should pass if current node fails filters but another node
        # is suitable when policy=on-demand.
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        extra_specs = {'volume_backend_name': 'lvm1'}
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI',
                                        'extra_specs': extra_specs},
                        'volume_properties': {'project_id': 1,
                                              'size': 200,
                                              'node': 'node4'}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        node_state = sched.find_retype_node(ctx, request_spec,
                                            filter_properties={},
                                            migration_policy='on-demand')
        self.assertEqual('node1', utils.extract_node(node_state.node))

    @mock.patch('cinder.db.service_get_all')
    def test_retype_policy_demand_migrate_fail(self, _mock_service_get_topic):
        # Retype should fail if current node doesn't pass filters and
        # no other suitable candidates exist even if policy=on-demand.
        sched, ctx = self._node_passes_filters_setup(
            _mock_service_get_topic)
        extra_specs = {'volume_backend_name': 'lvm1'}
        request_spec = {'volume_id': fake.VOLUME_ID,
                        'volume_type': {'name': 'LVM_iSCSI',
                                        'extra_specs': extra_specs},
                        'volume_properties': {'project_id': 1,
                                              'size': 2048,
                                              'node': 'node4'}}
        request_spec = objects.RequestSpec.from_primitives(request_spec)
        self.assertRaises(exception.NoValidNode, sched.find_retype_node, ctx,
                          request_spec, filter_properties={},
                          migration_policy='on-demand')
