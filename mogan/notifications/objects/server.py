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

from mogan.notifications.objects import base
from mogan.objects import base as mogan_base
from mogan.objects import fields


@mogan_base.MoganObjectRegistry.register_notification
class ServerPayload(base.NotificationPayloadBase):
    SCHEMA = {
        'name': ('server', 'name'),
        'uuid': ('server', 'uuid'),
        'user_id': ('server', 'user_id'),
        'project_id': ('server', 'project_id'),
        'availability_zone': ('server', 'availability_zone'),
        'image_uuid': ('server', 'image_uuid'),
        'created_at': ('server', 'created_at'),
        'launched_at': ('server', 'launched_at'),
        'updated_at': ('server', 'updated_at'),
        'status': ('server', 'status'),
        'power_state': ('server', 'power_state'),
        'flavor_uuid': ('server', 'flavor_uuid'),
        'description': ('server', 'description'),
        'locked_by': ('server', 'locked_by'),
        'affinity_zone': ('server', 'affinity_zone'),
        'metadata': ('server', 'metadata'),
        'partitions': ('server', 'partitions'),
        'key_name': ('server', 'key_name'),
        'node': ('server', 'node')
    }
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'name': fields.StringField(nullable=False),
        'uuid': fields.UUIDField(nullable=False),
        'user_id': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'description': fields.StringField(nullable=True),
        'flavor_uuid': fields.UUIDField(nullable=False),
        'image_uuid': fields.UUIDField(nullable=True),
        'availability_zone': fields.StringField(nullable=True),
        'power_state': fields.StringField(nullable=True),
        'created_at': fields.DateTimeField(nullable=True),
        'launched_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'status': fields.StringField(nullable=True),
        'locked_by': fields.StringField(nullable=True),
        'affinity_zone': fields.StringField(nullable=True),
        'metadata': fields.FlexibleDictField(nullable=True),
        'partitions': fields.FlexibleDictField(nullable=True),
        'key_name': fields.StringField(nullable=True),
        'node': fields.StringField(nullable=True),
        'addresses': fields.ListOfObjectsField('ServerAddressesPayload',
                                               nullable=True)
    }

    def __init__(self, server):
        super(ServerPayload, self).__init__()
        self.populate_schema(server=server)
        self.addresses = ServerAddressesPayload.from_server_obj(server)


@mogan_base.MoganObjectRegistry.register_notification
class ServerAddressesPayload(base.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'port_id': fields.UUIDField(nullable=True),
        'mac_address': fields.MACAddressField(),
        'fixed_ips': fields.ListOfDictOfNullableStringsField(
            nullable=True),
        'network_id': fields.UUIDField(nullable=True),
        'floating_ip': fields.StringField(nullable=True),
        'preserve_on_delete': fields.BooleanField(nullable=True)
    }

    SCHEMA = {
        'port_id': ('nic', 'port_id'),
        'mac_address': ('nic', 'mac_address'),
        'fixed_ips': ('nic', 'fixed_ips'),
        'network_id': ('nic', 'network_id'),
        'floating_ip': ('nic', 'floating_ip'),
        'preserve_on_delete': ('nic', 'preserve_on_delete'),
    }

    def __init__(self, nic_obj):
        super(ServerAddressesPayload, self).__init__()
        self.populate_schema(nic=nic_obj)

    @classmethod
    def from_server_obj(cls, server):
        """Returns a list of a server's addresses.
        """
        if not server.nics:
            return []
        addresses = []
        for nic in server.nics:
            addresses.append(cls(nic))
        return addresses


@mogan_base.MoganObjectRegistry.register_notification
class ServerActionPayload(ServerPayload):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.0'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, server, fault):
        super(ServerActionPayload, self).__init__(server=server)
        self.fault = fault


@base.notification_sample('server-create-start.json')
@base.notification_sample('server-create-end.json')
@base.notification_sample('server-create-error.json')
@base.notification_sample('server-delete-start.json')
@base.notification_sample('server-delete-end.json')
@base.notification_sample('server-rebuild-start.json')
@base.notification_sample('server-rebuild-end.json')
@base.notification_sample('server-rebuild-error.json')
@mogan_base.MoganObjectRegistry.register_notification
class ServerActionNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('ServerActionPayload')
    }
