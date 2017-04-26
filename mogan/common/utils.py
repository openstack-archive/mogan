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

import base64
import binascii
import contextlib
import functools
import inspect
import os
import re
import shutil
import tempfile
import traceback

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from oslo_concurrency import lockutils
from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import encodeutils
import paramiko
import six

from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import states
from mogan.conf import CONF
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
    # If its a server method attempt to tack on the class name
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


def process_event(fsm, server, event=None):
    fsm.process_event(event)
    server.status = fsm.current_state
    server.save()


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


def _get_fault_detail(exc_info, error_code):
    details = ''
    if exc_info and error_code == 500:
        tb = exc_info[2]
        if tb:
            details = ''.join(traceback.format_tb(tb))
    return six.text_type(details)


def safe_truncate(value, length):
    """Safely truncates unicode strings such that their encoded length is
    no greater than the length provided.
    """
    b_value = encodeutils.safe_encode(value)[:length]

    decode_ok = False
    # NOTE[ZhongLuyao] UTF-8 character byte size varies from 1 to 6. If
    # truncating a long byte string to 255, the last character may be
    # cut in the middle, so that UnicodeDecodeError will occur when
    # converting it back to unicode.
    while not decode_ok:
        try:
            u_value = encodeutils.safe_decode(b_value)
            decode_ok = True
        except UnicodeDecodeError:
            b_value = b_value[:-1]
    return u_value


def add_server_fault_from_exc(context, server, fault, exc_info=None,
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
    message = safe_truncate(fault_message, 255)
    fault_dict = dict(exception=fault)
    fault_dict["message"] = message
    fault_dict["code"] = code
    fault_obj = objects.ServerFault(context=context)
    fault_obj.server_uuid = server.uuid
    fault_obj.update(fault_dict)
    code = fault_obj.code
    fault_obj.detail = _get_fault_detail(exc_info, code)
    fault_obj.create()


def execute(*cmd, **kwargs):
    """Convenience wrapper around oslo's execute() method.

    :param cmd: Passed to processutils.execute.
    :param use_standard_locale: True | False. Defaults to False. If set to
                                True, execute command with standard locale
                                added to environment variables.
    :returns: (stdout, stderr) from process execution
    :raises: UnknownArgumentError
    :raises: ProcessExecutionError
    """

    use_standard_locale = kwargs.pop('use_standard_locale', False)
    if use_standard_locale:
        env = kwargs.pop('env_variables', os.environ.copy())
        env['LC_ALL'] = 'C'
        kwargs['env_variables'] = env
    result = processutils.execute(*cmd, **kwargs)
    LOG.debug('Execution completed, command line is "%s"',
              ' '.join(map(str, cmd)))
    LOG.debug('Command stdout is: "%s"', result[0])
    LOG.debug('Command stderr is: "%s"', result[1])
    return result


@contextlib.contextmanager
def tempdir(**kwargs):
    tempfile.tempdir = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**kwargs)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error('Could not remove tmpdir: %s', e)


def mkfs(fs, path, label=None, run_as_root=False):
    """Format a file or block device

    :param fs: Filesystem type (examples include 'swap', 'ext3', 'ext4'
               'btrfs', etc.)
    :param path: Path to file or block device to format
    :param label: Volume label to use
    """
    if fs == 'swap':
        args = ['mkswap']
    else:
        args = ['mkfs', '-t', fs]
    # add -F to force no interactive execute on non-block device.
    if fs in ('ext3', 'ext4', 'ntfs'):
        args.extend(['-F'])
    if label:
        if fs in ('msdos', 'vfat'):
            label_opt = '-n'
        else:
            label_opt = '-L'
        args.extend([label_opt, label])
    args.append(path)
    execute(*args, run_as_root=run_as_root)


def trycmd(*args, **kwargs):
    """Convenience wrapper around oslo's trycmd() method."""
    return processutils.trycmd(*args, **kwargs)


def check_string_length(value, name=None, min_length=0, max_length=None):
    """Check the length of specified string
    :param value: the value of the string
    :param name: the name of the string
    :param min_length: the min_length of the string
    :param max_length: the max_length of the string
    """
    if not isinstance(value, six.string_types):
        if name is None:
            msg = "The input is not a string or unicode"
        else:
            msg = "%s is not a string or unicode" % name
        raise exception.Invalid(message=msg)

    if name is None:
        name = value

    if len(value) < min_length:
        msg = _("%(name)s has a minimum character requirement of "
                "%(min_length)s.") % {'name': name, 'min_length': min_length}
        raise exception.Invalid(message=msg)

    if max_length and len(value) > max_length:
        msg = _("%(name)s has more than %(max_length)s "
                "characters.") % {'name': name, 'max_length': max_length}
        raise exception.Invalid(message=msg)


def _create_x509_openssl_config(conffile, upn):
    content = ("distinguished_name  = req_distinguished_name\n"
               "[req_distinguished_name]\n"
               "[v3_req_client]\n"
               "extendedKeyUsage = clientAuth\n"
               "subjectAltName = otherName:""1.3.6.1.4.1.311.20.2.3;UTF8:%s\n")

    with open(conffile, 'w') as file:
        file.write(content % upn)


def generate_winrm_x509_cert(user_id, bits=2048):
    """Generate a cert for passwordless auth for user in project."""
    subject = '/CN=%s' % user_id
    upn = '%s@localhost' % user_id

    with tempdir() as tmpdir:
        keyfile = os.path.abspath(os.path.join(tmpdir, 'temp.key'))
        conffile = os.path.abspath(os.path.join(tmpdir, 'temp.conf'))

        _create_x509_openssl_config(conffile, upn)

        (certificate, _err) = execute(
            'openssl', 'req', '-x509', '-nodes', '-days', '3650',
            '-config', conffile, '-newkey', 'rsa:%s' % bits,
            '-outform', 'PEM', '-keyout', keyfile, '-subj', subject,
            '-extensions', 'v3_req_client',
            binary=True)

        (out, _err) = execute('openssl', 'pkcs12', '-export',
                              '-inkey', keyfile, '-password', 'pass:',
                              process_input=certificate,
                              binary=True)

        private_key = base64.b64encode(out)
        fingerprint = generate_x509_fingerprint(certificate)
        if six.PY3:
            private_key = private_key.decode('ascii')
            certificate = certificate.decode('utf-8')

    return (private_key, certificate, fingerprint)


def generate_fingerprint(public_key):
    try:
        pub_bytes = public_key.encode('utf-8')
        # Test that the given public_key string is a proper ssh key. The
        # returned object is unused since pyca/cryptography does not have a
        # fingerprint method.
        serialization.load_ssh_public_key(
            pub_bytes, backends.default_backend())
        pub_data = base64.b64decode(public_key.split(' ')[1])
        digest = hashes.Hash(hashes.MD5(), backends.default_backend())
        digest.update(pub_data)
        md5hash = digest.finalize()
        raw_fp = binascii.hexlify(md5hash)
        if six.PY3:
            raw_fp = raw_fp.decode('ascii')
        return ':'.join(a + b for a, b in zip(raw_fp[::2], raw_fp[1::2]))
    except Exception:
        raise exception.InvalidKeypair(
            reason=_('failed to generate fingerprint'))


def generate_x509_fingerprint(pem_key):
    try:
        if isinstance(pem_key, six.text_type):
            pem_key = pem_key.encode('utf-8')
        cert = x509.load_pem_x509_certificate(
            pem_key, backends.default_backend())
        raw_fp = binascii.hexlify(cert.fingerprint(hashes.SHA1()))
        if six.PY3:
            raw_fp = raw_fp.decode('ascii')
        return ':'.join(a + b for a, b in zip(raw_fp[::2], raw_fp[1::2]))
    except (ValueError, TypeError, binascii.Error) as ex:
        raise exception.InvalidKeypair(
            reason=_('failed to generate X509 fingerprint. '
                     'Error message: %s') % ex)


def generate_key_pair(bits=2048):
    key = paramiko.RSAKey.generate(bits)
    keyout = six.StringIO()
    key.write_private_key(keyout)
    private_key = keyout.getvalue()
    public_key = '%s %s Generated-by-Mogan' % (
        key.get_name(), key.get_base64())
    fingerprint = generate_fingerprint(public_key)
    return (private_key, public_key, fingerprint)
