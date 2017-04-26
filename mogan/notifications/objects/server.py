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
        'description': ('server', 'description')
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
        # 'network_info'
        # 'extra'
    }

    def __init__(self, server, **kwargs):
        super(ServerPayload, self).__init__(**kwargs)
        self.populate_schema(server=server)


@mogan_base.MoganObjectRegistry.register_notification
class ServerActionPayload(ServerPayload):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.0'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, server, fault, **kwargs):
        super(ServerActionPayload, self).__init__(
            server=server,
            fault=fault,
            **kwargs)


@mogan_base.MoganObjectRegistry.register_notification
class ServerActionNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('ServerActionPayload')
    }
