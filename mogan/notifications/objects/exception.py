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
import inspect

import six

from mogan.notifications.objects import base
from mogan.objects import base as moban_base
from mogan.objects import fields


@moban_base.MoganObjectRegistry.register_notification
class ExceptionPayload(base.NotificationPayloadBase):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'module_name': fields.StringField(),
        'function_name': fields.StringField(),
        'exception': fields.StringField(),
        'exception_message': fields.StringField()
    }

    @classmethod
    def from_exception(cls, fault):
        trace = inspect.trace()[-1]
        module = inspect.getmodule(trace[0])
        module_name = module.__name__ if module else 'unknown'
        return cls(
            function_name=trace[3],
            module_name=module_name,
            exception=fault.__class__.__name__,
            exception_message=six.text_type(fault))
