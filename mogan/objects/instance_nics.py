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
        'instance_uuid': object_fields.UUIDField(nullable=True),
        'mac_address': object_fields.MACAddressField(nullable=True),
        'network_id': object_fields.UUIDField(nullable=True),
        'fixed_ip': object_fields.StringField(nullable=True),
        'port_type': object_fields.StringField(nullable=True),
        'floating_ip': object_fields.StringField(nullable=True),
        'deleted': object_fields.BooleanField(default=False),
        'deleted_at': object_fields.DateTimeField(nullable=True),
    }


@base.MoganObjectRegistry.register
class InstanceNicList(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    fields = {
        'objects': object_fields.ListOfObjectsField('InstanceNic'),
        }

    def get_by_instance_uuid(self, context, instance_uuid):
        nics = self.dbapi.instance_nics_get_by_instance_uuid(
            context, instance_uuid)
        return object_base.obj_make_list(context, self,
                                         InstanceNic, nics)

    def save(self, context):
        if 'instance_nics' in self.obj_what_changed():
            nw_inst_nics = self.fields['instance_nics'].to_primitive(
                self, 'instance_nics', self.instance_nics)
            self.dbapi.instance_nic_update_or_create(
                self.port_id, nw_inst_nics)
        self.obj_reset_changes()
