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
class Flavor(base.NimbleObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'name': object_fields.StringField(nullable=True),
        'description': object_fields.StringField(nullable=True),
        'is_public': object_fields.BooleanField(),
    }

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Flavor._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context):
        """Return a list of Flavor objects."""
        db_flavors = cls.dbapi.flavor_get_all()
        return Flavor._from_db_object_list(db_flavors, cls, context)

    def create(self, context=None):
        """Create a Flavor record in the DB."""
        values = self.obj_get_changes()
        db_flavor = self.dbapi.flavor_create(values)
        self._from_db_object(self, db_flavor)
