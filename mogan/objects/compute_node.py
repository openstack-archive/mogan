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
        'availability_zone': object_fields.StringField(nullable=True),
        'node_uuid': object_fields.UUIDField(read_only=True),
        'capabilities': object_fields.FlexibleDictField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
    }

    @classmethod
    def list(cls, context):
        """Return a list of ComputeNode objects."""
        db_compute_nodes = cls.dbapi.compute_node_get_all(context)
        return cls._from_db_object_list(context, db_compute_nodes)

    @classmethod
    def get(cls, context, node_uuid):
        """Find a compute node and return a ComputeNode object."""
        db_compute_node = cls.dbapi.compute_node_get(context, node_uuid)
        compute_node = cls._from_db_object(cls(context), db_compute_node)
        return compute_node

    def create(self, context=None):
        """Create a ComputeNode record in the DB."""
        values = self.obj_get_changes()
        db_compute_node = self.dbapi.compute_node_create(context, values)
        self._from_db_object(self, db_compute_node)

    def destroy(self, context=None):
        """Delete the ComputeNode from the DB."""
        self.dbapi.compute_node_destroy(context, self.node_uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this ComputeNode."""
        updates = self.obj_get_changes()
        self.dbapi.compute_node_update(context, self.node_uuid, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.node_uuid)
        self.obj_refresh(current)
