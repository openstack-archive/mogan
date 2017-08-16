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

from oslo_log import log as logging
from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields

LOG = logging.getLogger(__name__)


@base.MoganObjectRegistry.register
class ServerGroup(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),

        'user_id': object_fields.StringField(nullable=True),
        'project_id': object_fields.StringField(nullable=True),

        'uuid': object_fields.UUIDField(),
        'name': object_fields.StringField(nullable=True),

        'policies': object_fields.ListOfStringsField(nullable=True),
        'members': object_fields.ListOfStringsField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, server_group, db_server):
        """Method to help with migration to objects.

        Converts a database entity to a formal object.
        """
        for field in server_group.fields:
            server_group[field] = db_server[field]
        server_group._context = context
        server_group.obj_reset_changes()
        return server_group

    def create(self):
        values = self.obj_get_changes()
        policies = values.pop('policies', None)
        members = values.pop('members', None)
        db_group = self.dbapi.server_group_create(self._context, values,
                                                  policies=policies,
                                                  members=members)
        self._from_db_object(self._context, self, db_group)

    @classmethod
    def get_by_uuid(cls, context, uuid):
        db_group = cls.dbapi.server_group_get(context, uuid)
        return cls._from_db_object(context, cls(), db_group)

    def destroy(self):
        self.dbapi.server_group_delete(self._context, self.uuid)
        self.obj_reset_changes()

    @classmethod
    def add_members(cls, context, group_uuid, members):
        cls.dbapi.server_group_members_add(context, group_uuid, members)

    def save(self, context=None):
        updates = self.obj_get_changes()
        self.dbapi.server_group_update(context, self.uuid, updates)
        self.obj_reset_changes()


@base.MoganObjectRegistry.register
class ServerGroupList(object_base.ObjectListBase, base.MoganObject,
                      object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ServerGroup'),
    }

    @classmethod
    def get_all(cls, context):
        db_groups = cls.dbapi.server_group_get_all(context)
        return object_base.obj_make_list(context, cls(context), ServerGroup,
                                         db_groups)

    @classmethod
    def get_by_project_id(cls, context, project_id):
        project_server_groups = cls.dbapi.server_group_get_all(
            context, project_id)
        return object_base.obj_make_list(context, cls(context), ServerGroup,
                                         project_server_groups)
