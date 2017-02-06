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
        'fixed_ips': object_fields.ListOfDictOfNullableStringsField(
            nullable=True),
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
        'nics': object_fields.ListOfObjectsField('InstanceNic')}

    @classmethod
    def get_by_instance_uuid(cls, context, instance_uuid):
        nics = cls.dbapi.instance_nics_get_by_instance_uuid(
            context, instance_uuid)
        return cls.from_list_dict(context, instance_uuid, nics)

    def to_list_dict(self):
        blob = [{'port_id': x.port_id,
                 'mac_address': x.mac_address,
                 'network_id': x.network_id,
                 'fixed_ips': x.fixed_ips,
                 'port_type': x.port_type,
                 'floating_ip': x.floating_ip} for x in self.nics]
        return blob

    # TODO(liusheng) this is for temporarily keep the return of API save as
    # before, it is better to refactor the API return format
    def to_legacy_dict(self):
        legacy_network_info = {}
        for nic in self.nics:
            port = {nic.port_id: {'network': nic.network_id,
                                  'mac_address': nic.mac_address,
                                  'fixed_ips': nic.fixed_ips}}
            legacy_network_info.update(port)
        return legacy_network_info

    def get_port_ids(self):
        return [x.port_id for x in self.nics]

    @classmethod
    def from_list_dict(cls, context, instance_uuid, raw_nics):
        self = cls(context=context, nics=[],
                   instance_uuid=instance_uuid)
        if raw_nics is not None:
            nics = (raw_nics if isinstance(raw_nics, list) else
                    jsonutils.loads(raw_nics))
        else:
            nics = []
        for nic in nics:
            # Note(moshele): is_new is deprecated and therefore we load it
            # with default value of False
            nic_obj = InstanceNic(
                port_id=nic.get('port_id', ''),
                mac_address=nic.get('mac_address', ''),
                network_id=nic.get('network_id', ''),
                fixed_ips=nic.get('fixed_ips', []),
                port_type=nic.get('port_type', ''),
                floating_ip=nic.get('floating_ip', ''))
            nic_obj.obj_reset_changes()
            self.nics.append(nic_obj)
        self.obj_reset_changes()
        return self

    def save(self, create_new=False):
        values = self.obj_get_changes()
        update_nics = []
        if 'nics' in values:
            for nic in values['nics'] or []:
                nic_dict = nic.obj_get_changes()
                nic_dict.update(port_id=nic.port_id)
                update_nics.append(nic_dict)
                nic.obj_reset_changes()
        elif create_new:
            update_nics = self.to_list_dict()
        else:
            return
        for nic in update_nics:
            nic.update(instance_uuid=self.instance_uuid)
            port_id = nic.pop('port_id', None)
            self.dbapi.instance_nic_update_or_create(self._context,
                                                     port_id,
                                                     nic)
