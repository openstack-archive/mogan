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

from oslo_serialization import jsonutils
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
        'port_id': object_fields.UUIDField(nullable=True),
        'mac_address': object_fields.MACAddressField(nullable=True),
        'network_id': object_fields.UUIDField(nullable=True),
        'fixed_ip': object_fields.StringField(nullable=True),
        'port_type': object_fields.StringField(nullable=True),
        'floating_ip': object_fields.StringField(nullable=True),
    }


@base.MoganObjectRegistry.register
class InstanceNics(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'instance_uuid': object_fields.UUIDField(),
        'nics': object_fields.ListOfObjectsField('InstanceNic'),
        }

    def get_by_instance_uuid(self, context, instance_uuid):
        nics = self.dbapi.instance_nics_get_by_instance_uuid(
            context, instance_uuid)
        return self.obj_from_db(context, instance_uuid, nics)

    @classmethod
    def obj_from_db(cls, context, instance_uuid, db_nics):
        self = cls(context=context, nics=[],
                   instance_uuid=instance_uuid)
        if db_nics is not None:
            nics = jsonutils.loads(db_nics)
        else:
            nics = []
        for nic in nics:
            # Note(moshele): is_new is deprecated and therefore we load it
            # with default value of False
            nic_obj = InstanceNic(
                port_id=nic['port_id'], mac_address=nic['mac_address'],
                network_id=nic['network_id'], fixed_ip=nic['fixed_ip'],
                port_type=nic['port_type'], floating_ip=nic['floating_ip'])
            nic_obj.obj_reset_changes()
            self.nics.append(nic_obj)
        self.obj_reset_changes()
        return self

    def to_json(self):
        blob = [{'port_id': x.port_id,
                 'mac_address': x.mac_address,
                 'network_id': x.network_id,
                 'fixed_ip': x.fixed_ip,
                 'port_type': x.port_type,
                 'floating_ip': x.floating_ip} for x in self.nics]
        return jsonutils.dumps(blob)

    def save(self, context):
        values = self.obj_get_changes()
        if 'nics' in values:
            for nic in values['nics']:
                nic