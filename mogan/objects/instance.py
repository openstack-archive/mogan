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

from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_versionedobjects import base as object_base

from mogan.common.i18n import _LE
from mogan.db import api as dbapi
from mogan import objects
from mogan.objects import base
from mogan.objects import fields as object_fields

OPTIONAL_ATTRS = ['fault', ]


LOG = logging.getLogger(__name__)


@base.MoganObjectRegistry.register
class Instance(base.MoganObject, object_base.VersionedObjectDictCompat):
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
        'power_state': object_fields.StringField(nullable=True),
        'instance_type_uuid': object_fields.UUIDField(nullable=True),
        'availability_zone': object_fields.StringField(nullable=True),
        'image_uuid': object_fields.UUIDField(nullable=True),
        'network_info': object_fields.FlexibleDictField(nullable=True),
        'node_uuid': object_fields.UUIDField(nullable=True),
        'launched_at': object_fields.DateTimeField(nullable=True),
        'extra': object_fields.FlexibleDictField(nullable=True),
        'deleted': object_fields.BooleanField(default=False),
        'deleted_at': object_fields.DateTimeField(nullable=True),
        'locked': object_fields.BooleanField(default=False),
        'locked_by': object_fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(instance, db_inst, expected_attrs=None):
        """Method to help with migration to objects.

        Converts a database entity to a formal object.

        :param instance: An object of the Instance class.
        :param db_inst: A DB Instance model of the object
        :return: The object of the class with the database entity added
        """
        for field in set(instance.fields) - set(OPTIONAL_ATTRS):
            instance[field] = db_inst[field]

        if expected_attrs is None:
            expected_attrs = []
        if 'fault' in expected_attrs:
            instance._load_fault(instance._context, instance.uuid)
        instance.obj_reset_changes()
        return instance

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        instances = []
        for obj in db_objects:
            expected_attrs = []
            if obj["status"] == "error":
                expected_attrs.append("fault")
            instances.append(Instance._from_db_object(cls(context),
                                                      obj,
                                                      expected_attrs))
        return instances

    def _load_fault(self, context, instance_uuid):
        self.fault = objects.InstanceFault.get_latest_for_instance(
            context=context, instance_uuid=instance_uuid)

    @classmethod
    def list(cls, context, project_only=False):
        """Return a list of Instance objects."""
        db_instances = cls.dbapi.instance_get_all(context,
                                                  project_only=project_only)
        return Instance._from_db_object_list(db_instances, cls, context)

    @classmethod
    def get(cls, context, uuid):
        """Find a instance and return a Instance object."""
        expected_attrs = []
        db_instance = cls.dbapi.instance_get(context, uuid)
        if db_instance["status"] == "error":
            expected_attrs.append("fault")
        instance = Instance._from_db_object(cls(context),
                                            db_instance,
                                            expected_attrs)
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
        for field in self.fields:
            if (self.obj_attr_is_set(field) and
                    isinstance(self.fields[field], object_fields.ObjectField)):
                try:
                    getattr(self, '_save_%s' % field)(context)
                except AttributeError:
                    LOG.exception(_LE('No save handler for %s'), field,
                                  instance=self)
                except db_exc.DBReferenceError as exp:
                    if exp.key != 'instance_uuid':
                        raise
        self.dbapi.instance_update(context, self.uuid, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.uuid)
        self.obj_refresh(current)
        self.obj_reset_changes()
