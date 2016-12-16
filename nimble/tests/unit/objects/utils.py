# Copyright 2016 Intel
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
"""Nimble object test utilities."""
import six

from nimble.common import exception
from nimble.common.i18n import _
from nimble import objects
from nimble.tests.unit.db import utils as db_utils


def check_keyword_arguments(func):
    @six.wraps(func)
    def wrapper(**kw):
        obj_type = kw.pop('object_type')
        result = func(**kw)

        extra_args = set(kw) - set(result)
        if extra_args:
            raise exception.InvalidParameterValue(
                _("Unknown keyword arguments (%(extra)s) were passed "
                  "while creating a test %(object_type)s object.") %
                {"extra": ", ".join(extra_args),
                 "object_type": obj_type})

        return result

    return wrapper


def get_test_instance(ctxt, **kw):
    """Return a Instance object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    kw['object_type'] = 'instance'
    get_db_instance_checked = check_keyword_arguments(
        db_utils.get_test_instance)
    db_instance = get_db_instance_checked(**kw)
    instance = objects.Instance(ctxt)
    for key in db_instance:
        setattr(instance, key, db_instance[key])
    return instance


def create_test_instance(ctxt, **kw):
    """Create and return a test instance object.

    Create a instance in the DB and return a Instance object with appropriate
    attributes.
    """
    instance = get_test_instance(ctxt, **kw)
    instance.create()
    return instance
