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
import copy

from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields


@base.MoganObjectRegistry.register
class ServerNic(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'port_id': object_fields.UUIDField(nullable=False),
        'server_uuid': object_fields.UUIDField(nullable=True),
        'mac_address': object_fields.MACAddressField(nullable=True),
        'network_id': object_fields.UUIDField(nullable=True),
        'fixed_ips': object_fields.ListOfDictOfNullableStringsField(
            nullable=True),
        'floating_ip': object_fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, obj, db_object, server_uuid=None):
        if server_uuid:
            db_object = copy.deepcopy(db_object)
            db_object.update(server_uuid=server_uuid)
        if not isinstance(db_object, dict):
            db_object_dict = db_object.as_dict()
        else:
            db_object_dict = db_object
        obj = ServerNic(context)
        obj.update(db_object_dict)
        obj.obj_reset_changes()
        return obj

    def save(self, context):
        updates = self.obj_get_changes()
        self.dbapi.server_nic_update_or_create(
            context, self.port_id, updates)

    def create(self, context):
        values = self.obj_to_primitive()['mogan_object.data']
        self.dbapi.server_nic_update_or_create(
            context, self.port_id, values)

    def delete(self, context):
        self.dbapi.server_nic_delete(
            context, self.port_id)


@base.MoganObjectRegistry.register
class ServerNics(object_base.ObjectListBase, base.MoganObject,
                 object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('ServerNic')}

    def __init__(self, context=None, **kwargs):

        super(ServerNics, self).__init__(context=context, **kwargs)

    @classmethod
    def get_by_server_uuid(cls, context, server_uuid):
        nics = cls.dbapi.server_nics_get_by_server_uuid(
            context, server_uuid)
        return object_base.obj_make_list(context, cls(context), ServerNic,
                                         nics)

    def create(self, context):
        for nic_obj in self:
            nic_obj.create(context)

    def as_list_of_dict(self):
        return [obj.obj_to_primitive()['mogan_object.data'] for obj in self]

    def get_port_ids(self):
        return [x.port_id for x in self]

    def delete(self, context):
        for nic_obj in self:
            nic_obj.delete(context)
