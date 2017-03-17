# Copyright 2017 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
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

from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import compute_port
from mogan.objects import fields as object_fields


@base.MoganObjectRegistry.register
class ComputeNode(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(read_only=True),
        'cpus': object_fields.IntegerField(),
        'memory_mb': object_fields.IntegerField(),
        'hypervisor_type': object_fields.StringField(),
        'node_type': object_fields.StringField(),
        'availability_zone': object_fields.StringField(nullable=True),
        'node_uuid': object_fields.UUIDField(read_only=True),
        'ports': object_fields.ObjectField('ComputePortList', nullable=True),
        'extra_specs': object_fields.FlexibleDictField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, node, db_node):
        """Converts a database entity to a formal object."""
        for field in node.fields:
            if field == 'ports':
                node.ports = object_base.obj_make_list(
                    context, compute_port.ComputePortList(context),
                    compute_port.ComputePort, db_node['ports']
                )
            else:
                node[field] = db_node[field]
        node.obj_reset_changes()
        return node

    @classmethod
    def get(cls, context, node_uuid):
        """Find a compute node and return a ComputeNode object."""
        db_compute_node = cls.dbapi.compute_node_get(context, node_uuid)
        compute_node = cls._from_db_object(
            context, cls(context), db_compute_node)
        return compute_node

    def create(self, context=None):
        """Create a ComputeNode record in the DB."""
        values = self.obj_get_changes()
        self.dbapi.compute_node_create(context, values)

    def destroy(self, context=None):
        """Delete the ComputeNode from the DB."""
        self.dbapi.compute_node_destroy(context, self.node_uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this ComputeNode."""
        updates = self.obj_get_changes()
        self.dbapi.compute_node_update(context, self.node_uuid, updates)
        self.obj_reset_changes()

    def update_from_driver(self, node):
        keys = ["cpus", "memory_mb", "hypervisor_type", "node_type",
                "availability_zone", "node_uuid", "extra_specs"]
        for key in keys:
            if key in node:
                setattr(self, key, node[key])


@base.MoganObjectRegistry.register
class ComputeNodeList(object_base.ObjectListBase, base.MoganObject,
                      object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ComputeNode')
    }

    @classmethod
    def get_all(cls, context):
        db_compute_nodes = cls.dbapi.compute_node_get_all(context)
        return object_base.obj_make_list(context, cls(context),
                                         ComputeNode, db_compute_nodes)
