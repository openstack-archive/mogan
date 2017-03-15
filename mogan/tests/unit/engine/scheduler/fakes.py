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
#
"""
Fakes For Scheduler tests.
"""

from oslo_versionedobjects import base as object_base
from oslo_versionedobjects import fields

from mogan.engine.scheduler import filter_scheduler
from mogan.engine.scheduler import node_manager
from mogan.objects import base
from mogan.objects import fields as object_fields


class FakeFilterScheduler(filter_scheduler.FilterScheduler):
    def __init__(self, *args, **kwargs):
        super(FakeFilterScheduler, self).__init__(*args, **kwargs)
        self.node_manager = node_manager.NodeManager()


@base.MoganObjectRegistry.register
class FakeNode(base.MoganObject, object_base.VersionedObjectDictCompat):
    fields = {
        'id': object_fields.IntegerField(),
        'node_uuid': object_fields.UUIDField(),
        'node_type': object_fields.StringField(nullable=True),
        'availability_zone': object_fields.StringField(nullable=True),
        'extra_specs': object_fields.FlexibleDictField(nullable=True),
        'ports': fields.ListOfDictOfNullableStringsField(nullable=True),
    }


fakenode1 = FakeNode(id=1,
                     node_uuid='1a617131-cdbc-45dc-afff-f21f17ae054e',
                     extra_specs={},
                     availability_zone='az1',
                     node_type='type1',
                     ports=[])
fakenode2 = FakeNode(id=2,
                     node_uuid='2a617131-cdbc-45dc-afff-f21f17ae054e',
                     extra_specs={},
                     availability_zone='az1',
                     node_type='type1',
                     ports=[])
fakenode3 = FakeNode(id=3,
                     node_uuid='3a617131-cdbc-45dc-afff-f21f17ae054e',
                     extra_specs={},
                     availability_zone='az1',
                     node_type='type1',
                     ports=[])


class FakeNodeState(node_manager.NodeState):
    def __init__(self, node, attribute_dict):
        super(FakeNodeState, self).__init__(node)
        for (key, val) in attribute_dict.items():
            setattr(self, key, val)
