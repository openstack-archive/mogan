# Copyright 2016 Huawei Technologies Co.,LTD.
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


@base.NimbleObjectRegistry.register
class Instance(base.NimbleObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'uuid': object_fields.UUIDField(nullable=True),
        'name': object_fields.StringField(nullable=True),
        'description': object_fields.StringField(nullable=True),
        'project_id': object_fields.UUIDField(nullable=True),
        'user_id': object_fields.UUIDField(nullable=True),
        'status': object_fields.StringField(nullable=True),
        'instance_type_uuid': object_fields.UUIDField(nullable=True),
        'availability_zone': object_fields.StringField(nullable=True),
        'image_uuid': object_fields.UUIDField(nullable=True),
        'network_info': object_fields.FlexibleDictField(nullable=True),
        'node_uuid': object_fields.UUIDField(nullable=True),
        'launched_at': object_fields.DateTimeField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
        'deleted': object_fields.BooleanField(default=False),
        'deleted_at': object_fields.DateTimeField(nullable=True),
    }

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Instance._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context, project_only=False):
        """Return a list of Instance objects."""
        db_instances = cls.dbapi.instance_get_all(context,
                                                  project_only=project_only)
        return Instance._from_db_object_list(db_instances, cls, context)

    @classmethod
    def get(cls, context, uuid):
        """Find a instance and return a Instance object."""
        db_instance = cls.dbapi.instance_get(context, uuid)
        instance = Instance._from_db_object(cls(context), db_instance)
        return instance

    def create(self, context=None):
        """Create a Instance record in the DB."""
        values = self.obj_get_changes()
        # Since we need to avoid passing False down to the DB layer
        # (which uses an integer), we can always default it to zero here.
        values['deleted'] = 0

        db_instance = self.dbapi.instance_create(context, values)
        self._from_db_object(self, db_instance)

    def destroy(self, context=None):
        """Delete the Instance from the DB."""
        self.dbapi.instance_destroy(context, self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Instance."""
        updates = self.obj_get_changes()
        self.dbapi.instance_update(context, self.uuid, updates)
        self.obj_reset_changes()
