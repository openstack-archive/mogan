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

from mogan.common import exception
from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields


@base.NimbleObjectRegistry.register
class InstanceType(base.NimbleObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'uuid': object_fields.UUIDField(nullable=True),
        'name': object_fields.StringField(nullable=True),
        'description': object_fields.StringField(nullable=True),
        'is_public': object_fields.BooleanField(),
        'extra_specs': object_fields.FlexibleDictField(),
    }

    def __init__(self, *args, **kwargs):
        super(InstanceType, self).__init__(*args, **kwargs)
        self._orig_extra_specs = {}

    def obj_reset_changes(self, fields=None, recursive=False):
        super(InstanceType, self).obj_reset_changes(fields=fields,
                                                    recursive=recursive)
        if fields is None or 'extra_specs' in fields:
            self._orig_extra_specs = (dict(self.extra_specs)
                                      if self.obj_attr_is_set('extra_specs')
                                      else {})

    def obj_what_changed(self):
        changes = super(InstanceType, self).obj_what_changed()
        if ('extra_specs' in self and
                self.extra_specs != self._orig_extra_specs):
            changes.add('extra_specs')
        return changes

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [InstanceType._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context):
        """Return a list of Instance Type objects."""
        db_instance_types = cls.dbapi.instance_type_get_all(context)
        return InstanceType._from_db_object_list(db_instance_types, cls,
                                                 context)

    @classmethod
    def get(cls, context, instance_type_uuid):
        """Find a Instance Type and return a Instance Type object."""
        db_instance_type = cls.dbapi.instance_type_get(context,
                                                       instance_type_uuid)
        instance_type = InstanceType._from_db_object(cls(context),
                                                     db_instance_type)
        return instance_type

    def create(self, context=None):
        """Create a Instance Type record in the DB."""
        values = self.obj_get_changes()
        db_instance_type = self.dbapi.instance_type_create(context, values)
        self._from_db_object(self, db_instance_type)

    def destroy(self, context=None):
        """Delete the Instance Type from the DB."""
        self.dbapi.instance_type_destroy(context, self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        updates = self.obj_get_changes()
        extra_specs = updates.pop('extra_specs', None)
        if updates:
            raise exception.ObjectActionError(
                action='save', reason='read-only fields were changed')

        if extra_specs is not None:
            deleted_keys = (set(self._orig_extra_specs.keys()) -
                            set(extra_specs.keys()))
            added_keys = self.extra_specs
        else:
            added_keys = deleted_keys = None

        if added_keys or deleted_keys:
            self.save_extra_specs(context, self.extra_specs, deleted_keys)

    def save_extra_specs(self, context, to_add=None, to_delete=None):
        """Add or delete extra_specs.

        :param:to_add: A dict of new keys to add/update
        :param:to_delete: A list of keys to remove
        """
        ident = self.uuid

        to_add = to_add if to_add is not None else {}
        to_delete = to_delete if to_delete is not None else []

        if to_add:
            self.dbapi.extra_specs_update_or_create(context, ident, to_add)

        for key in to_delete:
            self.dbapi.type_extra_specs_delete(context, ident, key)
        self.obj_reset_changes(['extra_specs'])
