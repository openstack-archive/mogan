# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
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

import ast
import hashlib
import inspect
import six

from oslo_versionedobjects import fields as object_fields

from mogan.common import utils

Field = object_fields.Field
ObjectField = object_fields.ObjectField
ListOfObjectsField = object_fields.ListOfObjectsField
ListOfDictOfNullableStringsField \
    = object_fields.ListOfDictOfNullableStringsField


class IntegerField(object_fields.IntegerField):
    pass


class UUIDField(object_fields.UUIDField):
    pass


class StringField(object_fields.StringField):
    pass


class StringAcceptsCallable(object_fields.String):
    @staticmethod
    def coerce(obj, attr, value):
        if callable(value):
            value = value()
        return super(StringAcceptsCallable, StringAcceptsCallable).coerce(
            obj, attr, value)


class StringFieldThatAcceptsCallable(object_fields.StringField):
    """Custom StringField object that allows for functions as default

    In some cases we need to allow for dynamic defaults based on configuration
    options, this StringField object allows for a function to be passed as a
    default, and will only process it at the point the field is coerced
    """

    AUTO_TYPE = StringAcceptsCallable()

    def __repr__(self):
        default = self._default
        if (self._default != object_fields.UnspecifiedDefault and
                callable(self._default)):
            default = "%s-%s" % (
                self._default.__name__,
                hashlib.md5(inspect.getsource(
                    self._default).encode()).hexdigest())
        return '%s(default=%s,nullable=%s)' % (self._type.__class__.__name__,
                                               default, self._nullable)


class DateTimeField(object_fields.DateTimeField):
    pass


class BooleanField(object_fields.BooleanField):
    pass


class ListOfStringsField(object_fields.ListOfStringsField):
    pass


class FlexibleDict(object_fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if isinstance(value, six.string_types):
            value = ast.literal_eval(value)
        return dict(value)


class FlexibleDictField(object_fields.AutoTypedField):
    AUTO_TYPE = FlexibleDict()

    # TODO(lucasagomes): In our code we've always translated None to {},
    # this method makes this field to work like this. But probably won't
    # be accepted as-is in the oslo_versionedobjects library
    def _null(self, obj, attr):
        if self.nullable:
            return {}
        super(FlexibleDictField, self)._null(obj, attr)


class MACAddress(object_fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        return utils.validate_and_normalize_mac(value)


class MACAddressField(object_fields.AutoTypedField):
    AUTO_TYPE = MACAddress()


class BaseMoganEnum(object_fields.Enum):
    def __init__(self, **kwargs):
        super(BaseMoganEnum, self).__init__(valid_values=self.__class__.ALL)


class NotificationPriority(BaseMoganEnum):
    AUDIT = 'audit'
    CRITICAL = 'critical'
    DEBUG = 'debug'
    INFO = 'info'
    ERROR = 'error'
    SAMPLE = 'sample'
    WARN = 'warn'

    ALL = (AUDIT, CRITICAL, DEBUG, INFO, ERROR, SAMPLE, WARN)


class NotificationPhase(BaseMoganEnum):
    START = 'start'
    END = 'end'
    ERROR = 'error'

    ALL = (START, END, ERROR)


class NotificationAction(BaseMoganEnum):
    UPDATE = 'update'
    EXCEPTION = 'exception'
    DELETE = 'delete'
    POWER_ON = 'power_on'
    POWER_OFF = 'power_off'
    REBOOT = 'reboot'
    SHUTDOWN = 'shutdown'
    CREATE = 'create'

    ALL = (UPDATE, EXCEPTION, DELETE, CREATE, POWER_OFF)


class NotificationPhaseField(object_fields.BaseEnumField):
    AUTO_TYPE = NotificationPhase()


class NotificationActionField(object_fields.BaseEnumField):
    AUTO_TYPE = NotificationAction()


class NotificationPriorityField(object_fields.BaseEnumField):
    AUTO_TYPE = NotificationPriority()
