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

from nimble.db import api as dbapi
from nimble.objects import base
from nimble.objects import fields as object_fields


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
        'status': object_fields.StringField(nullable=True),
        'power_state': object_fields.StringField(nullable=True),
        'task_state': object_fields.StringField(nullable=True),
        'instance_type_id': object_fields.IntegerField(nullable=True),
        'availability_zone': object_fields.StringField(nullable=True),
        'node_uuid': object_fields.UUIDField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
    }

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Instance._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context):
        """Return a list of Instance objects."""
        db_instances = cls.dbapi.instance_get_all()
        return Instance._from_db_object_list(db_instances, cls, context)

    @classmethod
    def get(cls, context, instance_id):
        """Find a instance and return a Instance object."""
        db_instance = cls.dbapi.instance_get(instance_id)
        instance = Instance._from_db_object(cls(context), db_instance)
        return instance

    def create(self, context=None):
        """Create a Instance record in the DB."""
        values = self.obj_get_changes()
        db_instance = self.dbapi.instance_create(values)
        self._from_db_object(self, db_instance)

    def destroy(self, context=None):
        """Delete the Instance from the DB."""
        self.dbapi.instance_destroy(self.uuid)
        self.obj_reset_changes()
