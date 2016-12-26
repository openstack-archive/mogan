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

import contextlib
import re
import shutil
import tempfile

from oslo_concurrency import lockutils
from oslo_concurrency import processutils
from oslo_log import log as logging
import six

from mogan.common import exception
from mogan.common.i18n import _LW
from mogan.common.i18n import _LE
import mogan.conf


CONF = mogan.conf.CONF
LOG = logging.getLogger(__name__)

synchronized = lockutils.synchronized_with_prefix('mogan-')


@contextlib.contextmanager
def tempdir(**kwargs):
    argdict = kwargs.copy()
    if 'dir' not in argdict:
        argdict['dir'] = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**argdict)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error(_LE('Could not remove tmpdir: %s'), e)


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


def get_root_helper():
    # FIXME(Shaohe) need to support rootwrap
    return 'sudo'


def execute(*cmd, **kwargs):
    """Convenience wrapper around oslo's execute() method."""

    if 'run_as_root' in kwargs and kwargs.get('run_as_root'):
        # FIXME (Shaohe) need to support rootwrap daemon
        return RootwrapProcessHelper().execute(*cmd, **kwargs)
    return processutils.execute(*cmd, **kwargs)


class RootwrapProcessHelper(object):
    def trycmd(self, *cmd, **kwargs):
        kwargs['root_helper'] = get_root_helper()
        return processutils.trycmd(*cmd, **kwargs)

    def execute(self, *cmd, **kwargs):
        kwargs['root_helper'] = get_root_helper()
        return processutils.execute(*cmd, **kwargs)


def sanitize_hostname(hostname):
    """Return a hostname which conforms to RFC-952 and RFC-1123 specs except
    the length of hostname.

    Window, Linux, and Dnsmasq has different limitation:

    Windows: 255 (net_bios limits to 15, but window will truncate it)
    Linux: 64
    Dnsmasq: 63

    chose 63.

    """

    def truncate_hostname(name):
        if len(name) > 63:
            LOG.warning(_LW("Hostname %(hostname)s is longer than 63, "
                            "truncate it to %(truncated_name)s"),
                            {'hostname': name, 'truncated_name': name[:63]})
        return name[:63]

    if isinstance(hostname, six.text_type):
        # Remove characters outside the Unicode range U+0000-U+00FF
        hostname = hostname.encode('latin-1', 'ignore')
        if six.PY3:
            hostname = hostname.decode('latin-1')

    hostname = truncate_hostname(hostname)
    hostname = re.sub('[ _]', '-', hostname)
    hostname = re.sub('[^\w.-]+', '', hostname)
    hostname = hostname.lower()
    hostname = hostname.strip('.-')
