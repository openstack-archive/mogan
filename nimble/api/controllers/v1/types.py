# Copyright 2013 Red Hat, Inc.
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

import inspect
import json

from oslo_utils import strutils
from oslo_utils import uuidutils
import six
import wsme
from wsme import types as wtypes

from nimble.common import exception
from nimble.common.i18n import _


class UuidType(wtypes.UserType):
    """A simple UUID type."""

    basetype = wtypes.text
    name = 'uuid'

    @staticmethod
    def validate(value):
        if not uuidutils.is_uuid_like(value):
            raise exception.InvalidUUID(uuid=value)
        return value

    @staticmethod
    def frombasetype(value):
        if value is None:
            return None
        return UuidType.validate(value)


class BooleanType(wtypes.UserType):
    """A simple boolean type."""

    basetype = wtypes.text
    name = 'boolean'

    @staticmethod
    def validate(value):
        try:
            return strutils.bool_from_string(value, strict=True)
        except ValueError as e:
            # raise Invalid to return 400 (BadRequest) in the API
            raise exception.Invalid(e)

    @staticmethod
    def frombasetype(value):
        if value is None:
            return None
        return BooleanType.validate(value)


class JsonType(wtypes.UserType):
    """A simple JSON type."""

    basetype = wtypes.text
    name = 'json'

    def __str__(self):
        # These are the json serializable native types
        return ' | '.join(map(str, (wtypes.text, six.integer_types, float,
                                    BooleanType, list, dict, None)))

    @staticmethod
    def validate(value):
        try:
            json.dumps(value)
        except TypeError:
            raise exception.Invalid(_('%s is not JSON serializable') % value)
        else:
            return value

    @staticmethod
    def frombasetype(value):
        return JsonType.validate(value)


class ListType(wtypes.UserType):
    """A simple list type."""

    basetype = wtypes.text
    name = 'list'

    @staticmethod
    def validate(value):
        """Validate and convert the input to a ListType.

        :param value: A comma separated string of values
        :returns: A list of unique values, whose order is not guaranteed.
        """
        items = [v.strip().lower() for v in six.text_type(value).split(',')]
        # filter() to remove empty items
        # set() to remove duplicated items
        return list(set(filter(None, items)))

    @staticmethod
    def frombasetype(value):
        if value is None:
            return None
        return ListType.validate(value)


boolean = BooleanType()
uuid = UuidType()
# Can't call it 'json' because that's the name of the stdlib module
jsontype = JsonType()
listtype = ListType()


class JsonPatchType(wtypes.Base):
    """A complex type that represents a single json-patch operation."""

    path = wtypes.wsattr(wtypes.StringType(pattern='^(/[\w-]+)+$'),
                         mandatory=True)
    op = wtypes.wsattr(wtypes.Enum(str, 'add', 'replace', 'remove'),
                       mandatory=True)
    value = wsme.wsattr(jsontype, default=wtypes.Unset)

    # The class of the objects being patched. Override this in subclasses.
    # Should probably be a subclass of nimble.api.controllers.base.APIBase.
    _api_base = None

    # Attributes that are not required for construction, but which may not be
    # removed if set. Override in subclasses if needed.
    _extra_non_removable_attrs = set()

    # Set of non-removable attributes, calculated lazily.
    _non_removable_attrs = None

    @staticmethod
    def internal_attrs():
        """Returns a list of internal attributes.

        Internal attributes can't be added, replaced or removed. This
        method may be overwritten by derived class.

        """
        return ['/created_at', '/id', '/links', '/updated_at', '/uuid']

    @classmethod
    def non_removable_attrs(cls):
        """Returns a set of names of attributes that may not be removed.

        Attributes whose 'mandatory' property is True are automatically added
        to this set. To add additional attributes to the set, override the
        field _extra_non_removable_attrs in subclasses, with a set of the form
        {'/foo', '/bar'}.
        """
        if cls._non_removable_attrs is None:
            cls._non_removable_attrs = cls._extra_non_removable_attrs.copy()
            if cls._api_base:
                fields = inspect.getmembers(cls._api_base,
                                            lambda a: not inspect.isroutine(a))
                for name, field in fields:
                    if getattr(field, 'mandatory', False):
                        cls._non_removable_attrs.add('/%s' % name)
        return cls._non_removable_attrs

    @staticmethod
    def validate(patch):
        _path = '/' + patch.path.split('/')[1]
        if _path in patch.internal_attrs():
            msg = _("'%s' is an internal attribute and can not be updated")
            raise wsme.exc.ClientSideError(msg % patch.path)

        if patch.path in patch.non_removable_attrs() and patch.op == 'remove':
            msg = _("'%s' is a mandatory attribute and can not be removed")
            raise wsme.exc.ClientSideError(msg % patch.path)

        if patch.op != 'remove':
            if patch.value is wsme.Unset:
                msg = _("'add' and 'replace' operations need a value")
                raise wsme.exc.ClientSideError(msg)

        ret = {'path': patch.path, 'op': patch.op}
        if patch.value is not wsme.Unset:
            ret['value'] = patch.value
        return ret
