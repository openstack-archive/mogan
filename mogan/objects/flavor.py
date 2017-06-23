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


OPTIONAL_FIELDS = ['projects']


@base.MoganObjectRegistry.register
class Flavor(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'uuid': object_fields.UUIDField(nullable=True),
        'name': object_fields.StringField(nullable=True),
        'description': object_fields.StringField(nullable=True),
        'is_public': object_fields.BooleanField(),
        'disabled': object_fields.BooleanField(),
        'resources': object_fields.FlexibleDictField(nullable=True),
        'resource_traits': object_fields.FlexibleDictField(nullable=True),
        'projects': object_fields.ListOfStringsField(),
    }

    def __init__(self, *args, **kwargs):
        super(Flavor, self).__init__(*args, **kwargs)
        self._orig_projects = {}

    @staticmethod
    def _from_db_object(context, flavor, db_flavor, expected_attrs=None):
        if expected_attrs is None:
            expected_attrs = []

        for name, field in flavor.fields.items():
            if name in OPTIONAL_FIELDS:
                continue
            value = db_flavor[name]
            if isinstance(field, object_fields.IntegerField):
                value = value if value is not None else 0
            flavor[name] = value

        if 'projects' in expected_attrs:
            flavor._load_projects(context)

        flavor.obj_reset_changes()
        return flavor

    def _load_projects(self, context):
        self.projects = [x['project_id'] for x in
                         self.dbapi.flavor_access_get(context, self.uuid)]
        self.obj_reset_changes(['projects'])

    def obj_reset_changes(self, fields=None, recursive=False):
        super(Flavor, self).obj_reset_changes(fields=fields,
                                              recursive=recursive)
        if fields is None or 'projects' in fields:
            self._orig_projects = (list(self.projects)
                                   if self.obj_attr_is_set('projects')
                                   else [])

    def obj_what_changed(self):
        changes = super(Flavor, self).obj_what_changed()
        if 'projects' in self and self.projects != self._orig_projects:
            changes.add('projects')
        return changes

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Flavor._from_db_object(context, cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context):
        """Return a list of Flavor objects."""
        db_flavors = cls.dbapi.flavor_get_all(context)
        return Flavor._from_db_object_list(db_flavors, cls, context)

    @classmethod
    def get(cls, context, flavor_uuid):
        """Find a Flavor and return a Flavor object."""
        db_flavor = cls.dbapi.flavor_get(context, flavor_uuid)
        flavor = Flavor._from_db_object(
            context, cls(context), db_flavor,
            expected_attrs=['projects'])
        return flavor

    def create(self, context=None):
        """Create a Flavor record in the DB."""
        values = self.obj_get_changes()
        db_flavor = self.dbapi.flavor_create(context, values)
        self._from_db_object(context, self, db_flavor)

    def destroy(self, context=None):
        """Delete the Flavor from the DB."""
        self.dbapi.flavor_destroy(context, self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        updates = self.obj_get_changes()
        projects = updates.pop('projects', None)

        # access projects
        if projects is not None:
            deleted_projects = set(self._orig_projects) - set(projects)
            added_projects = set(projects) - set(self._orig_projects)
        else:
            added_projects = deleted_projects = None

        if added_projects or deleted_projects:
            self.save_projects(context, added_projects, deleted_projects)

        self.dbapi.flavor_update(context, self.uuid, updates)

    def save_projects(self, context, to_add=None, to_delete=None):
        """Add or delete projects.

        :param:to_add: A list of projects to add
        :param:to_delete: A list of projects to remove
        """
        ident = self.uuid

        to_add = to_add if to_add is not None else []
        to_delete = to_delete if to_delete is not None else []

        for project_id in to_add:
            self.dbapi.flavor_access_add(context, ident, project_id)

        for project_id in to_delete:
            self.dbapi.flavor_access_remove(context, ident, project_id)
        self.obj_reset_changes(['projects'])
