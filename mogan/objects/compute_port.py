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
class ComputePort(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(read_only=True),
        'port_type': object_fields.StringField(),
        'port_uuid': object_fields.UUIDField(read_only=True),
        'node_uuid': object_fields.UUIDField(read_only=True),
        'extra_specs': object_fields.FlexibleDictField(nullable=True),
    }

    @classmethod
    def list(cls, context):
        """Return a list of ComputePort objects."""
        db_compute_ports = cls.dbapi.compute_port_get_all(context)
        return cls._from_db_object_list(context, db_compute_ports)

    @classmethod
    def get(cls, context, port_uuid):
        """Find a compute port and return a ComputePort object."""
        db_compute_port = cls.dbapi.compute_port_get(context, port_uuid)
        compute_port = cls._from_db_object(cls(context), db_compute_port)
        return compute_port

    def create(self, context=None):
        """Create a ComputePort record in the DB."""
        values = self.obj_get_changes()
        db_compute_port = self.dbapi.compute_port_create(context, values)
        self._from_db_object(self, db_compute_port)

    def destroy(self, context=None):
        """Delete the ComputePort from the DB."""
        self.dbapi.compute_port_destroy(context, self.port_uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this ComputePort."""
        updates = self.obj_get_changes()
        self.dbapi.compute_port_update(context, self.port_uuid, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.port_uuid)
        self.obj_refresh(current)

    def update_from_driver(self, port):
        keys = ["port_type", "port_uuid", "node_uuid", "extra_specs"]
        for key in keys:
            if key in port:
                setattr(self, key, port[key])


@base.MoganObjectRegistry.register
class ComputePortList(object_base.ObjectListBase, base.MoganObject,
                      object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ComputePort')
    }

    @classmethod
    def get_by_node_uuid(cls, context, node_uuid):
        db_ports = cls.dbapi.compute_port_get_by_node_uuid(
            context, node_uuid)
        return object_base.obj_make_list(context, cls(context),
                                         ComputePort, db_ports)
