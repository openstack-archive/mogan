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
class InstanceNic(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'port_id': object_fields.UUIDField(nullable=False),
        'instance_uuid': object_fields.UUIDField(nullable=True),
        'mac_address': object_fields.MACAddressField(nullable=True),
        'network_id': object_fields.UUIDField(nullable=True),
        'fixed_ips': object_fields.ListOfDictOfNullableStringsField(
            nullable=True),
        'port_type': object_fields.StringField(nullable=True),
        'floating_ip': object_fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, obj, db_object, instance_uuid=None):
        if instance_uuid:
            db_object = copy.deepcopy(db_object)
            db_object.update(instance_uuid=instance_uuid)
        if not isinstance(db_object, dict):
            db_object_dict = db_object.as_dict()
        else:
            db_object_dict = db_object
        obj = InstanceNic(context)
        obj.update(db_object_dict)
        obj.obj_reset_changes()
        return obj

    def save(self, context):
        updates = self.obj_get_changes()
        self.dbapi.instance_nic_update_or_create(
            context, self.port_id, updates)

    def create(self, context):
        values = self.obj_to_primitive()['mogan_object.data']
        self.dbapi.instance_nic_update_or_create(
            context, self.port_id, values)


@base.MoganObjectRegistry.register
class InstanceNics(object_base.ObjectListBase, base.MoganObject,
                   object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('InstanceNic')}

    def __init__(self, context=None, **kwargs):

        super(InstanceNics, self).__init__(context=context, **kwargs)

    @classmethod
    def get_by_instance_uuid(cls, context, instance_uuid):
        nics = cls.dbapi.instance_nics_get_by_instance_uuid(
            context, instance_uuid)
        return object_base.obj_make_list(context, cls(context), InstanceNic,
                                         nics)

    def create(self, context):
        for nic_obj in self:
            nic_obj.create(context)

    def as_list_of_dict(self):
        return [obj.obj_to_primitive()['mogan_object.data'] for obj in self]

    # TODO(liusheng) this is for temporarily keep the return of API save as
    # before, it is better to refactor the API return format
    def to_legacy_dict(self):
        legacy_network_info = {}
        for nic in self:
            port = {nic.port_id: {'network': nic.network_id,
                                  'mac_address': nic.mac_address,
                                  'fixed_ips': nic.fixed_ips}}
            legacy_network_info.update(port)
        return legacy_network_info

    def get_port_ids(self):
        return [x.port_id for x in self]
