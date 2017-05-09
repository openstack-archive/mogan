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
class ServerFault(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'server_uuid': object_fields.UUIDField(),
        'code': object_fields.IntegerField(),
        'message': object_fields.StringField(nullable=True),
        'detail': object_fields.StringField(nullable=True),
    }

    def return_dict(self):
        return dict((k, getattr(self, k))
                    for k in ['code', 'message', 'detail']
                    if hasattr(self, k))

    @staticmethod
    def _from_db_object(context, fault, db_fault):
        for key in fault.fields:
            fault[key] = db_fault[key]
        fault._context = context
        fault.obj_reset_changes()
        return fault

    @classmethod
    def get_latest_for_server(cls, context, server_uuid):
        db_faults = cls.dbapi.server_fault_get_by_server_uuids(
            context, [server_uuid])
        if server_uuid in db_faults and db_faults[server_uuid]:
            return cls._from_db_object(context, cls(),
                                       db_faults[server_uuid][0])

    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        values = {
            'server_uuid': self.server_uuid,
            'code': self.code,
            'message': self.message,
            'detail': self.detail,
        }
        db_fault = self.dbapi.server_fault_create(self._context, values)
        self._from_db_object(self._context, self, db_fault)
        self.obj_reset_changes()


@base.MoganObjectRegistry.register
class ServerFaultList(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ServerFault')
    }

    @classmethod
    def get_by_server_uuids(cls, context, server_uuids):
        db_faultdict = cls.dbapi.server_fault_get_by_server_uuids(
            context, server_uuids)
        db_faultlist = itertools.chain(*db_faultdict.values())
        return object_base.obj_make_list(context, cls(context),
                                         objects.ServerFault,
                                         db_faultlist)
