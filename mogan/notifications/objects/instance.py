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
class InstancePayload(base.NotificationPayloadBase):
    SCHEMA = {
        'name': ('instance', 'name'),
        'uuid': ('instance', 'uuid'),
        'user_id': ('instance', 'user_id'),
        'project_id': ('instance', 'project_id'),
        'availability_zone': ('instance', 'availability_zone'),
        'image_uuid': ('instance', 'image_uuid'),
        'created_at': ('instance', 'created_at'),
        'launched_at': ('instance', 'launched_at'),
        'updated_at': ('instance', 'updated_at'),
        'status': ('instance', 'status'),
        # TODO(liusheng) the instance object hasn't power_state attribute
        # 'power_state': ('instance', 'power_state'),
        'instance_type_uuid': ('instance', 'instance_type_uuid'),
        'description': ('instance', 'description')
    }
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'name': fields.StringField(nullable=False),
        'uuid': fields.UUIDField(nullable=False),
        'user_id': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'description': fields.StringField(nullable=True),
        'instance_type_uuid': fields.UUIDField(nullable=False),
        'image_uuid': fields.UUIDField(nullable=True),
        'availability_zone': fields.StringField(nullable=True),
        # 'power_state':  fields.StringField(nullable=True),
        'created_at': fields.DateTimeField(nullable=True),
        'launched_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'status': fields.StringField(nullable=True),
        # 'network_info'
        # 'extra'
    }

    def __init__(self, instance, **kwargs):
        super(InstancePayload, self).__init__(**kwargs)
        self.populate_schema(instance=instance)


@mogan_base.MoganObjectRegistry.register_notification
class InstanceActionPayload(InstancePayload):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.0'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, instance, fault, **kwargs):
        super(InstanceActionPayload, self).__init__(
            instance=instance,
            fault=fault,
            **kwargs)


@mogan_base.MoganObjectRegistry.register_notification
class InstanceActionNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('InstanceActionPayload')
    }
