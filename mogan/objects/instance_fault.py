# Copyright 2017 Intel
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

import itertools

from oslo_versionedobjects import base as object_base

from mogan.common import exception
from mogan.db import api as dbapi
from mogan import objects
from mogan.objects import base
from mogan.objects import fields as object_fields


@base.MoganObjectRegistry.register
class InstanceFault(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'instance_uuid': object_fields.UUIDField(),
        'code': object_fields.IntegerField(),
        'created_at': object_fields.DateTimeField(),
        'message': object_fields.StringField(nullable=True),
        'detail': object_fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, fault, db_fault):
        for key in fault.fields:
            fault[key] = db_fault[key]
        fault._context = context
        fault.obj_reset_changes()
        return fault

    @object_base.remotable_classmethod
    def get_latest_for_instance(cls, context, instance_uuid):
        db_faults = cls.dbapi.instance_fault_get_by_instance_uuids(
            context,
            [instance_uuid])
        if instance_uuid in db_faults and db_faults[instance_uuid]:
            return cls._from_db_object(context, cls(),
                                       db_faults[instance_uuid][0])

    @object_base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        values = {
            'instance_uuid': self.instance_uuid,
            'code': self.code,
            'message': self.message,
            'detail': self.detail,
            'created_at': self.created_at,
        }
        db_fault = self.dbapi.instance_fault_create(self._context, values)
        self._from_db_object(self._context, self, db_fault)
        self.obj_reset_changes()


@base.MoganObjectRegistry.register
class InstanceFaultList(base.MoganObject,
                        object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'faults': object_fields.ListOfObjectsField('InstanceFault')
    }

    @object_base.remotable_classmethod
    def get_by_instance_uuids(cls, context, instance_uuids):
        db_faultdict = cls.dbapi.instance_fault_get_by_instance_uuids(
            context, instance_uuids)
        db_faultlist = itertools.chain(*db_faultdict.values())
        return object_base.obj_make_list(context, cls(context),
                                         objects.InstanceFault,
                                         db_faultlist)
