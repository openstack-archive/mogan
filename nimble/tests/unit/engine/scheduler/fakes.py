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
#    License for the specific language governing permisnodesions and
#    limitations under the License.
#  
"""
Fakes For Scheduler tests.
"""

from oslo_utils import timeutils

from ironic.objects import node as ironic_node
from nimble.engine.manager import EngineManager
from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import node_manager


class FakeFilterScheduler(filter_scheduler.FilterScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeFilterScheduler, self).__init__(*args, **kwargs)
        self.node_manager = node_manager.NodeManager()


class FakeEngineManager(EngineManager):
    def __init__(self):
        super(EngineManager, self).__init__()

        node1 = ironic_node()
        node1['uuid'] = '111111'
        node1['capabilities'] = ''
        node1['availability_zone'] = 'az1'
        node1['instance_type'] = 'type1'
        self.node_cache[node1.uuid] = node1

        node2 = ironic_node()
        node2['uuid'] = '222222'
        node2['capabilities'] = ''
        node2['availability_zone'] = 'az2'
        node2['instance_type'] = 'type2'
        self.node_cache[node2.uuid] = node2

        node3 = ironic_node()
        node3['uuid'] = '333333'
        node3['capabilities'] = ''
        node3['availability_zone'] = 'az3'
        node3['instance_type'] = 'type3'
        self.node_cache[node3.uuid] = node3


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
