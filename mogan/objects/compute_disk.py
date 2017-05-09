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
class ComputeDisk(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(read_only=True),
        'disk_type': object_fields.StringField(),
        'size_gb': object_fields.IntegerField(),
        'disk_uuid': object_fields.UUIDField(read_only=True),
        'node_uuid': object_fields.UUIDField(read_only=True),
        'extra_specs': object_fields.FlexibleDictField(nullable=True),
    }

    @classmethod
    def list(cls, context):
        """Return a list of ComputeDisk objects."""
        db_compute_disks = cls.dbapi.compute_disk_get_all(context)
        return cls._from_db_object_list(context, db_compute_disks)

    @classmethod
    def get(cls, context, disk_uuid):
        """Find a compute disk and return a ComputeDisk object."""
        db_compute_disk = cls.dbapi.compute_disk_get(context, disk_uuid)
        compute_disk = cls._from_db_object(context, cls(context),
                                           db_compute_disk)
        return compute_disk

    def create(self, context=None):
        """Create a ComputeDisk record in the DB."""
        values = self.obj_get_changes()
        db_compute_disk = self.dbapi.compute_disk_create(context, values)
        self._from_db_object(context, self, db_compute_disk)

    def destroy(self, context=None):
        """Delete the ComputeDisk from the DB."""
        self.dbapi.compute_disk_destroy(context, self.disk_uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this ComputeDisk."""
        updates = self.obj_get_changes()
        self.dbapi.compute_disk_update(context, self.disk_uuid, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.disk_uuid)
        self.obj_refresh(current)


@base.MoganObjectRegistry.register
class ComputeDiskList(object_base.ObjectListBase, base.MoganObject,
                      object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ComputeDisk')
    }

    @classmethod
    def get_by_node_uuid(cls, context, node_uuid):
        db_disks = cls.dbapi.compute_disk_get_by_node_uuid(
            context, node_uuid)
        return object_base.obj_make_list(context, cls(context),
                                         ComputeDisk, db_disks)
