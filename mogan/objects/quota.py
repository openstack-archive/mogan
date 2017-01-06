# Copyright 2017 Fiberhome Integration Technologies Co.,LTD
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

from oslo_config import cfg
from oslo_utils import importutils
from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields


CONF = cfg.CONF


@base.MoganObjectRegistry.register
class Quota(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'project_id': object_fields.UUIDField(nullable=True),
        'resource': object_fields.StringField(nullable=True),
        'hard_limit': object_fields.IntegerField(nullable=True),
        'launched_at': object_fields.DateTimeField(nullable=True),
        'deleted': object_fields.BooleanField(default=False),
        'deleted_at': object_fields.DateTimeField(nullable=True),
    }

    def __init__(self, *args, **kwargs):
        super(Quota, self).__init__(*args, **kwargs)
        self.quota_driver = importutils.import_object(CONF.api.quota_driver)

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Quota._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context, project_only=False):
        """Return a list of Quota objects."""
        db_quotas = cls.dbapi.quota_get_all(context,
                                            project_only=project_only)
        return Quota._from_db_object_list(db_quotas, cls, context)

    @classmethod
    def get(cls, context, project_id):
        """Find a instance and return a Quota object."""
        db_quota = cls.dbapi.quota_get(context, project_id)
        quota = Quota._from_db_object(cls(context), db_quota)
        return quota

    def create(self, context=None):
        """Create a Quota record in the DB."""
        values = self.obj_get_changes()
        # Since we need to avoid passing False down to the DB layer
        # (which uses an integer), we can always default it to zero here.
        values['deleted'] = 0

        db_quota = self.dbapi.quota_create(context, values)
        self._from_db_object(self, db_quota)

    def destroy(self, context=None):
        """Delete the Quota from the DB."""
        self.dbapi.quota_destroy(context, self.project_id)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Instance."""
        updates = self.obj_get_changes()
        self.dbapi.quota_update(context, self.project_id, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.project_id)
        self.obj_refresh(current)
        self.obj_reset_changes()

    def reserve(self, context, expire=None, project_id=None, **deltas):
        return self.quota_driver.reserver(context, expire=None,
                                          project_id=None, **deltas)

    def commit(self, context, reservations, project_id=None):
        self.quota_driver.commit(context, reservations, project_id=None)

    def rollback(self, context, reservations, project_id=None):
        self.quota_driver.rollback(context, reservations, project_id=None)

    def count(self, context, resources, project_id=None):
        return self.driver.reserver(context, resources, project_id=None)
