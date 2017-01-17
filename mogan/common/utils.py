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

import eventlet
import functools
import re

from oslo_concurrency import lockutils
from oslo_context import context as common_context
from oslo_log import log as logging
import six

from mogan.common import exception
from mogan.common.i18n import _LW

LOG = logging.getLogger(__name__)

synchronized = lockutils.synchronized_with_prefix('mogan-')


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warning(_LW("Failed to remove trailing character. Returning "
                        "original object. Supplied object is not a string: "
                        "%s,"), value)
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
    :raises: InvalidMAC If the MAC address is not valid.

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


def spawn_n(func, *args, **kwargs):
    """Passthrough method for eventlet.spawn_n.

    This utility exists so that it can be stubbed for testing without
    interfering with the service spawns.

    It will also grab the context from the threadlocal store and add it to
    the store on the new thread.  This allows for continuity in logging the
    context when using this method to spawn a new thread.
    """
    _context = common_context.get_current()

    @functools.wraps(func)
    def context_wrapper(*args, **kwargs):
        # NOTE: If update_store is not called after spawn_n it won't be
        # available for the logger to pull from threadlocal storage.
        if _context is not None:
            _context.update_store()
        func(*args, **kwargs)

    eventlet.spawn_n(context_wrapper, *args, **kwargs)

