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
#
"""
Fakes For Scheduler tests.
"""

from oslo_versionedobjects import base as object_base


from nimble.engine.manager import EngineManager
from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import node_manager
from nimble.objects import base
from nimble.objects import fields as object_fields


class FakeFilterScheduler(filter_scheduler.FilterScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeFilterScheduler, self).__init__(*args, **kwargs)
        self.node_manager = node_manager.NodeManager()


@base.NimbleObjectRegistry.register
class FakeNode(base.NimbleObject, object_base.VersionedObjectDictCompat):
    fields = {
        'id': object_fields.IntegerField(),
        'uuid': object_fields.UUIDField(nullable=True),
        'properties': object_fields.FlexibleDictField(nullable=True),
    }


fakenode1 = FakeNode(id=1, uuid='1a617131-cdbc-45dc-afff-f21f17ae054e',
                     properties={'capabilities': '',
                                 'availability_zone': 'az1',
                                 'instance_type': 'type1'})
fakenode2 = FakeNode(id=2, uuid='2a617131-cdbc-45dc-afff-f21f17ae054e',
                     properties={'capabilities': '',
                                 'availability_zone': 'az2',
                                 'instance_type': 'type2'})
fakenode3 = FakeNode(id=3, uuid='3a617131-cdbc-45dc-afff-f21f17ae054e',
                     properties={'capabilities': '',
                                 'availability_zone': 'az3',
                                 'instance_type': 'type3'})


class FakeEngineManager(EngineManager):
    def __init__(self):
        super(EngineManager, self).__init__()

        self.node_cache[fakenode1.uuid] = fakenode1
        self.node_cache[fakenode2.uuid] = fakenode2
        self.node_cache[fakenode3.uuid] = fakenode3


class FakeNodeState(node_manager.NodeState):
    def __init__(self, node, attribute_dict):
        super(FakeNodeState, self).__init__(node)
        for (key, val) in attribute_dict.items():
            setattr(self, key, val)
