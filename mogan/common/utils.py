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

"""Utilities and helper functions."""

import functools
import inspect
import re
import traceback

from oslo_concurrency import lockutils
from oslo_log import log as logging
import six

from mogan.common import exception
from mogan.common import states
from mogan import objects


LOG = logging.getLogger(__name__)

synchronized = lockutils.synchronized_with_prefix('mogan-')


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warning("Failed to remove trailing character. Returning "
                    "original object. Supplied object is not a string: "
                    "%s,", value)
        return value

    return value.rstrip(chars) or value


def is_valid_mac(address):
    """Verify the format of a MAC address.

    Check if a MAC address is valid and contains six octets. Accepts
    colon-separated format only.

    :param address: MAC address to be validated.
    :returns: True if valid. False if not.

    """
    m = "[0-9a-f]{2}(:[0-9a-f]{2}){5}$"
    return (isinstance(address, six.string_types) and
            re.match(m, address.lower()))


def validate_and_normalize_mac(address):
    """Validate a MAC address and return normalized form.

    Checks whether the supplied MAC address is formally correct and
    normalize it to all lower case.

    :param address: MAC address to be validated and normalized.
    :returns: Normalized and validated MAC address.
    :raises InvalidMAC: If the MAC address is not valid.

    """
    if not is_valid_mac(address):
        raise exception.InvalidMAC(mac=address)
    return address.lower()


def make_pretty_name(method):
    """Makes a pretty name for a function/method."""
    meth_pieces = [method.__name__]
    # If its an instance method attempt to tack on the class name
    if hasattr(method, '__self__') and method.__self__ is not None:
        try:
            meth_pieces.insert(0, method.__self__.__class__.__name__)
        except AttributeError:
            pass
    return ".".join(meth_pieces)


def check_isinstance(obj, cls):
    """Checks that obj is of type cls, and lets PyLint infer types."""
    if isinstance(obj, cls):
        return obj
    raise Exception(_('Expected object of type: %s') % (str(cls)))


def get_state_machine(start_state=None, target_state=None):
    # Initialize state machine
    fsm = states.machine.copy()
    fsm.initialize(start_state=start_state, target_state=target_state)
    return fsm


def process_event(fsm, instance, event=None):
    fsm.process_event(event)
    instance.status = fsm.current_state
    instance.save()


def get_wrapped_function(function):
    """Get the method at the bottom of a stack of decorators."""
    if not hasattr(function, '__closure__') or not function.__closure__:
        return function

    def _get_wrapped_function(function):
        if not hasattr(function, '__closure__') or not function.__closure__:
            return None

        for closure in function.__closure__:
            func = closure.cell_contents

            deeper_func = _get_wrapped_function(func)
            if deeper_func:
                return deeper_func
            elif hasattr(closure.cell_contents, '__call__'):
                return closure.cell_contents

    return _get_wrapped_function(function)


def expects_func_args(*args):
    def _decorator_checker(dec):
        @functools.wraps(dec)
        def _decorator(f):
            base_f = get_wrapped_function(f)
            arg_names, a, kw, _default = inspect.getargspec(base_f)
            if a or kw or set(args) <= set(arg_names):
                return dec(f)
            else:
                raise TypeError("Decorated function %(f_name)s does not "
                                "have the arguments expected by the "
                                "decorator %(d_name)s" %
                                {'f_name': base_f.__name__,
                                 'd_name': dec.__name__})
        return _decorator
    return _decorator_checker


def _get_fault_details(exc_info, error_code):
    details = ''
    if exc_info and error_code == 500:
        tb = exc_info[2]
        if tb:
            details = ''.join(traceback.format_tb(tb))
    return six.text_type(details)


def add_instance_fault_from_exc(context, instance, fault, exc_info=None,
                                fault_message=None):
    """Adds the specified fault to the database."""
    code = 500
    if hasattr(fault, "kwargs"):
        code = fault.kwargs.get('code', 500)
    try:
        if not fault_message:
            fault_message = fault.format_message()
    except Exception:
        try:
            fault_message = six.text_type(fault)
        except Exception:
            fault_message = None
    if not fault_message:
        fault_message = fault.__class__.__name__
    fault_dict = dict(exception=fault)
    fault_dict["message"] = fault_message
    fault_dict["code"] = code
    fault_obj = objects.InstanceFault(context=context)
    fault_obj.instance_uuid = instance.uuid
    fault_obj.update(fault_dict)
    code = fault_obj.code
    fault_obj.details = _get_fault_details(exc_info, code)
    fault_obj.create()
