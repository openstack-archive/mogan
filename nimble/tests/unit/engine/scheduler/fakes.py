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
#    License for the specific language governing permisnodesions and limitations
#    under the License.
"""
Fakes For Scheduler tests.
"""

from oslo_utils import timeutils
from oslo_utils import uuidutils

from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import node_manager


class FakeFilterScheduler(filter_scheduler.FilterScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeFilterScheduler, self).__init__(*args, **kwargs)
        self.node_manager = node_manager.NodeManager()


class FakeNodeManager(node_manager.NodeManager):
    def __init__(self):
        super(FakeNodeManager, self).__init__()

        self.service_states = {
            'node1': {'capabilities': 1024,
                      'availability_zone': 1024,
                      'instance_type': 0},
            'node2': {'total_capacity_gb': 2048,
                      'free_capacity_gb': 300,
                      'allocated_capacity_gb': 1748,
                      'provisioned_capacity_gb': 1748,
                      'max_over_subscription_ratio': 1.5,
                      'thin_provisioning_support': True,
                      'thick_provisioning_support': False,
                      'reserved_percentage': 10,
                      'volume_backend_name': 'lvm2',
                      'timestamp': None},
            'node3': {'total_capacity_gb': 512,
                      'free_capacity_gb': 256,
                      'allocated_capacity_gb': 256,
                      'provisioned_capacity_gb': 256,
                      'max_over_subscription_ratio': 2.0,
                      'thin_provisioning_support': False,
                      'thick_provisioning_support': True,
                      'reserved_percentage': 0,
                      'volume_backend_name': 'lvm3',
                      'timestamp': None},
            'node4': {'total_capacity_gb': 2048,
                      'free_capacity_gb': 200,
                      'allocated_capacity_gb': 1848,
                      'provisioned_capacity_gb': 2047,
                      'max_over_subscription_ratio': 1.0,
                      'thin_provisioning_support': True,
                      'thick_provisioning_support': False,
                      'reserved_percentage': 5,
                      'volume_backend_name': 'lvm4',
                      'timestamp': None,
                      'consistencygroup_support': True},
            'node5': {'total_capacity_gb': 'infinite',
                      'free_capacity_gb': 'unknown',
                      'allocated_capacity_gb': 1548,
                      'provisioned_capacity_gb': 1548,
                      'max_over_subscription_ratio': 1.0,
                      'thin_provisioning_support': True,
                      'thick_provisioning_support': False,
                      'reserved_percentage': 5,
                      'timestamp': None},
        }


class FakeNodeState(node_manager.NodeState):
    def __init__(self, node, attribute_dict):
        super(FakeNodeState, self).__init__(node)
        for (key, val) in attribute_dict.items():
            setattr(self, key, val)


def mock_node_manager_db_calls(mock_obj, disabled=None):
    services = [
        dict(id=1, node='node1', topic='volume', disabled=False,
             availability_zone='zone1', updated_at=timeutils.utcnow()),
        dict(id=2, node='node2', topic='volume', disabled=False,
             availability_zone='zone1', updated_at=timeutils.utcnow()),
        dict(id=3, node='node3', topic='volume', disabled=False,
             availability_zone='zone2', updated_at=timeutils.utcnow()),
        dict(id=4, node='node4', topic='volume', disabled=False,
             availability_zone='zone3', updated_at=timeutils.utcnow()),
        dict(id=5, node='node5', topic='volume', disabled=False,
             availability_zone='zone3', updated_at=timeutils.utcnow()),
    ]
    if disabled is None:
        mock_obj.return_value = services
    else:
        mock_obj.return_value = [service for service in services
                                 if service['disabled'] == disabled]
