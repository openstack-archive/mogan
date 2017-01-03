# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Instance Metadata information."""

import base64
import os
import posixpath

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import importutils
from oslo_utils import timeutils
import six

from nimble.api.metadata import password
from nimble.api.metadata import vendordata
from nimble.api.metadata import vendordata_dynamic
from nimble.api.metadata import vendordata_json
import nimble.conf
from nimble import context
from nimble.engine import netutils
from nimble.i18n import _LI, _LW
from nimble import network
from nimble import objects
from nimble.objects import virt_device_metadata as metadata_obj
from nimble import utils


CONF = nimble.conf.CONF

VERSIONS = [
    '1.0',
    '2007-01-19',
    '2007-03-01',
    '2007-08-29',
    '2007-10-10',
    '2007-12-15',
    '2008-02-01',
    '2008-09-01',
    '2009-04-04',
]

# NOTE(mikal): think of these strings as version numbers. They traditionally
# correlate with OpenStack release dates, with all the changes for a given
# release bundled into a single version. Note that versions in the future are
# hidden from the listing, but can still be requested explicitly, which is
# required for testing purposes. We know this isn't great, but its inherited
# from EC2, which this needs to be compatible with.
FOLSOM = '2012-08-10'
GRIZZLY = '2013-04-04'
HAVANA = '2013-10-17'
LIBERTY = '2015-10-15'
NEWTON_ONE = '2016-06-30'
NEWTON_TWO = '2016-10-06'

OPENSTACK_VERSIONS = [
    FOLSOM,
    GRIZZLY,
    HAVANA,
    LIBERTY,
    NEWTON_ONE,
    NEWTON_TWO,
]

VERSION = "version"
CONTENT = "content"
CONTENT_DIR = "content"
MD_JSON_NAME = "meta_data.json"
VD_JSON_NAME = "vendor_data.json"
VD2_JSON_NAME = "vendor_data2.json"
NW_JSON_NAME = "network_data.json"
UD_NAME = "user_data"
PASS_NAME = "password"
MIME_TYPE_TEXT_PLAIN = "text/plain"
MIME_TYPE_APPLICATION_JSON = "application/json"

LOG = logging.getLogger(__name__)


class InvalidMetadataVersion(Exception):
    pass


class InvalidMetadataPath(Exception):
    pass


class InstanceMetadata(object):
    """Instance metadata."""

    def __init__(self, instance, address=None, content=None, extra_md=None,
                 network_info=None, vd_driver=None, network_metadata=None,
                 request_context=None):
        """Creation of this object should basically cover all time consuming
        collection.  Methods after that should not cause time delays due to
        network operations or lengthy cpu operations.

        The user should then get a single instance and make multiple method
        calls on it.
        """
        if not content:
            content = []

        ctxt = context.get_admin_context()

        # The default value of mimeType is set to MIME_TYPE_TEXT_PLAIN
        self.set_mimetype(MIME_TYPE_TEXT_PLAIN)
        self.instance = instance
        self.extra_md = extra_md

        # will support later 
        self.availability_zone = None
        self.security_groups = None 

        if instance.user_data is not None:
            self.userdata_raw = base64.b64decode(instance.user_data)
        else:
            self.userdata_raw = None

        self.address = address

        # expose instance metadata.
        self.launch_metadata = utils.instance_meta(instance)

        self.password = password.extract_password(instance)

        self.uuid = instance.uuid

        self.content = {}
        self.files = []

        # get network info, and the rendered network template
        if network_info is None:
            network_info = instance.info_cache.network_info

        # expose network metadata
        if network_metadata is None:
            self.network_metadata = netutils.get_network_metadata(network_info)
        else:
            self.network_metadata = network_metadata

        self.network_config = None
        cfg = netutils.get_injected_network_template(network_info)

        if cfg:
            key = "%04i" % len(self.content)
            self.content[key] = cfg
            self.network_config = {"name": "network_config",
                'content_path': "/%s/%s" % (CONTENT_DIR, key)}

        # 'content' is passed in from the configdrive code in
        # nimble/virt/libvirt/driver.py.  That's how we get the injected files
        # (personalities) in. AFAIK they're not stored in the db at all,
        # so are not available later (web service metadata time).
        for (path, contents) in content:
            key = "%04i" % len(self.content)
            self.files.append({'path': path,
                'content_path': "/%s/%s" % (CONTENT_DIR, key)})
            self.content[key] = contents

        if vd_driver is None:
            vdclass = importutils.import_class(CONF.vendordata_driver)
        else:
            vdclass = vd_driver

        self.vddriver = vdclass(instance=instance, address=address,
                                extra_md=extra_md, network_info=network_info)

        self.route_configuration = None

        # NOTE(mikal): the decision to not pass extra_md here like we
        # do to the StaticJSON driver is deliberate. extra_md will
        # contain the admin password for the instance, and we shouldn't
        # pass that to external services.
        self.vendordata_providers = {
            'StaticJSON': vendordata_json.JsonFileVendorData(
                instance=instance, address=address,
                extra_md=extra_md, network_info=network_info),
            'DynamicJSON': vendordata_dynamic.DynamicVendorData(
                instance=instance, address=address,
                network_info=network_info, context=request_context)
        }

    def _route_configuration(self):
        if self.route_configuration:
            return self.route_configuration

        path_handlers = {UD_NAME: self._user_data,
                         PASS_NAME: self._password,
                         VD_JSON_NAME: self._vendor_data,
                         VD2_JSON_NAME: self._vendor_data2,
                         MD_JSON_NAME: self._metadata_as_json,
                         NW_JSON_NAME: self._network_data,
                         VERSION: self._handle_version,
                         CONTENT: self._handle_content}

        self.route_configuration = RouteConfiguration(path_handlers)
        return self.route_configuration

    def set_mimetype(self, mime_type):
        self.md_mimetype = mime_type

    def get_mimetype(self):
        return self.md_mimetype

    def get_openstack_item(self, path_tokens):
        if path_tokens[0] == CONTENT_DIR:
            return self._handle_content(path_tokens)
        return self._route_configuration().handle_path(path_tokens)

    def _metadata_as_json(self, version, path):
        metadata = {'uuid': self.uuid}
        if self.launch_metadata:
            metadata['meta'] = self.launch_metadata
        if self.files:
            metadata['files'] = self.files
        if self.extra_md:
            metadata.update(self.extra_md)
        if self.network_config:
            metadata['network_config'] = self.network_config

        if self.instance.key_name:
            # need to support keypairs.
            else:
                keypairs = self.instance.keypairs
                # NOTE(mriedem): It's possible for the keypair to be deleted
                # before it was migrated to the instance_extra table, in which
                # case lazy-loading instance.keypairs will handle the 404 and
                # just set an empty KeyPairList object on the instance.
                keypair = keypairs[0] if keypairs else None

            if keypair:
                metadata['public_keys'] = {
                    keypair.name: keypair.public_key,
                }

                metadata['keys'] = [
                    {'name': keypair.name,
                     'type': keypair.type,
                     'data': keypair.public_key}
                ]
            else:
                LOG.debug("Unable to find keypair for instance with "
                          "key name '%s'.", self.instance.key_name,
                          instance=self.instance)

        metadata['hostname'] = self._get_hostname()
        metadata['name'] = self.instance.display_name
        metadata['launch_index'] = self.instance.launch_index
        # will support later
        # metadata['availability_zone'] = self.availability_zone

        if self._check_os_version(GRIZZLY, version):
            metadata['random_seed'] = base64.b64encode(os.urandom(512))

        if self._check_os_version(LIBERTY, version):
            metadata['project_id'] = self.instance.project_id

        # Baremetal does not need device_metadata
        # if self._check_os_version(NEWTON_ONE, version):
        #     metadata['devices'] = self._get_device_metadata()

        self.set_mimetype(MIME_TYPE_APPLICATION_JSON)
        return jsonutils.dump_as_bytes(metadata)

    def _handle_content(self, path_tokens):
        if len(path_tokens) == 1:
            raise KeyError("no listing for %s" % "/".join(path_tokens))
        if len(path_tokens) != 2:
            raise KeyError("Too many tokens for /%s" % CONTENT_DIR)
        return self.content[path_tokens[1]]

    def _handle_version(self, version, path):
        # request for /version, give a list of what is available
        ret = [MD_JSON_NAME]
        if self.userdata_raw is not None:
            ret.append(UD_NAME)
        if self._check_os_version(GRIZZLY, version):
            ret.append(PASS_NAME)
        if self._check_os_version(HAVANA, version):
            ret.append(VD_JSON_NAME)
        if self._check_os_version(LIBERTY, version):
            ret.append(NW_JSON_NAME)
        if self._check_os_version(NEWTON_TWO, version):
            ret.append(VD2_JSON_NAME)

        return ret

    def _user_data(self, version, path):
        if self.userdata_raw is None:
            raise KeyError(path)
        return self.userdata_raw

    def _network_data(self, version, path):
        if self.network_metadata is None:
            return jsonutils.dump_as_bytes({})
        return jsonutils.dump_as_bytes(self.network_metadata)

    def _password(self, version, path):
        if self._check_os_version(GRIZZLY, version):
            return password.handle_password
        raise KeyError(path)

    def _vendor_data(self, version, path):
        if self._check_os_version(HAVANA, version):
            self.set_mimetype(MIME_TYPE_APPLICATION_JSON)

            # NOTE(mikal): backwards compatibility... If the deployer has
            # specified providers, and one of those providers is StaticJSON,
            # then do that thing here. Otherwise, if the deployer has
            # specified an old style driver here, then use that. This second
            # bit can be removed once old style vendordata is fully deprecated
            # and removed.
            if (CONF.vendordata_providers and
                'StaticJSON' in CONF.vendordata_providers):
                return jsonutils.dump_as_bytes(
                    self.vendordata_providers['StaticJSON'].get())
            else:
                # TODO(mikal): when we removed the old style vendordata
                # drivers, we need to remove self.vddriver as well.
                return jsonutils.dump_as_bytes(self.vddriver.get())

        raise KeyError(path)

    def _vendor_data2(self, version, path):
        if self._check_os_version(NEWTON_TWO, version):
            self.set_mimetype(MIME_TYPE_APPLICATION_JSON)

            j = {}
            for provider in CONF.vendordata_providers:
                if provider == 'StaticJSON':
                    j['static'] = self.vendordata_providers['StaticJSON'].get()
                else:
                    values = self.vendordata_providers[provider].get()
                    for key in list(values):
                        if key in j:
                            LOG.warning(_LW('Removing duplicate metadata key: '
                                            '%s'), key, instance=self.instance)
                            del values[key]
                    j.update(values)

            return jsonutils.dump_as_bytes(j)

        raise KeyError(path)

    def _check_version(self, required, requested, versions=VERSIONS):
        return versions.index(requested) >= versions.index(required)

    def _check_os_version(self, required, requested):
        return self._check_version(required, requested, OPENSTACK_VERSIONS)

    def _get_hostname(self):
        return "%s%s%s" % (self.instance.hostname,
                           '.' if CONF.dhcp_domain else '',
                           CONF.dhcp_domain)

    def lookup(self, path):
        if path == "" or path[0] != "/":
            path = posixpath.normpath("/" + path)
        else:
            path = posixpath.normpath(path)

        # Set default mimeType. It will be modified only if there is a change
        self.set_mimetype(MIME_TYPE_TEXT_PLAIN)

        path_tokens = path.split('/')[1:]
        # all values of 'path' input starts with '/' and have no trailing /

        # specifically handle the top level request
        if len(path_tokens) == 1:
            if path_tokens[0] == "openstack":
                # NOTE(vish): don't show versions that are in the future
                today = timeutils.utcnow().strftime("%Y-%m-%d")
                versions = [v for v in OPENSTACK_VERSIONS if v <= today]
                if OPENSTACK_VERSIONS != versions:
                    LOG.debug("future versions %s hidden in version list",
                              [v for v in OPENSTACK_VERSIONS
                               if v not in versions], instance=self.instance)
                versions += ["latest"]
            else:
                versions = VERSIONS + ["latest"]
            return versions

        try:
            # we only support openstack, do not support ec2
            if path_tokens[0] == "openstack":
                data = self.get_openstack_item(path_tokens[1:])
        except (InvalidMetadataVersion, KeyError):
            raise InvalidMetadataPath(path)

        return data

    def metadata_for_config_drive(self):
        """Yields (path, value) tuples for metadata elements."""
        ALL_OPENSTACK_VERSIONS = OPENSTACK_VERSIONS + ["latest"]
        for version in ALL_OPENSTACK_VERSIONS:
            path = 'openstack/%s/%s' % (version, MD_JSON_NAME)
            yield (path, self.lookup(path))

            path = 'openstack/%s/%s' % (version, UD_NAME)
            if self.userdata_raw is not None:
                yield (path, self.lookup(path))

            if self._check_version(HAVANA, version, ALL_OPENSTACK_VERSIONS):
                path = 'openstack/%s/%s' % (version, VD_JSON_NAME)
                yield (path, self.lookup(path))

            if self._check_version(LIBERTY, version, ALL_OPENSTACK_VERSIONS):
                path = 'openstack/%s/%s' % (version, NW_JSON_NAME)
                yield (path, self.lookup(path))

            if self._check_version(NEWTON_TWO, version,
                                   ALL_OPENSTACK_VERSIONS):
                path = 'openstack/%s/%s' % (version, VD2_JSON_NAME)
                yield (path, self.lookup(path))

        for (cid, content) in six.iteritems(self.content):
            yield ('%s/%s/%s' % ("openstack", CONTENT_DIR, cid), content)


class RouteConfiguration(object):
    """Routes metadata paths to request handlers."""

    def __init__(self, path_handler):
        self.path_handlers = path_handler

    def _version(self, version):
        if version == "latest":
            version = OPENSTACK_VERSIONS[-1]

        if version not in OPENSTACK_VERSIONS:
            raise InvalidMetadataVersion(version)

        return version

    def handle_path(self, path_tokens):
        version = self._version(path_tokens[0])
        if len(path_tokens) == 1:
            path = VERSION
        else:
            path = '/'.join(path_tokens[1:])

        path_handler = self.path_handlers[path]

        if path_handler is None:
            raise KeyError(path)

        return path_handler(version, path)


def get_metadata_by_address(address):
    ctxt = context.get_admin_context()
    fixed_ip = network.API().get_fixed_ip_by_address(ctxt, address)
    LOG.info(_LI('Fixed IP %(ip)s translates to instance UUID %(uuid)s'),
             {'ip': address, 'uuid': fixed_ip['instance_uuid']})

    return get_metadata_by_instance_id(fixed_ip['instance_uuid'],
                                       address,
                                       ctxt)


def get_metadata_by_instance_id(instance_id, address, ctxt=None):
    ctxt = ctxt or context.get_admin_context()
    instance = objects.Instance.get_by_uuid(
        ctxt, instance_id, expected_attrs=['flavor', 'info_cache',
                                           'metadata', 'system_metadata',
                                           'keypairs', 'device_metadata'])
    return InstanceMetadata(instance, address)


def find_path_in_tree(data, path_tokens):
    # given a dict/list tree, and a path in that tree, return data found there.
    for i in range(0, len(path_tokens)):
        if isinstance(data, dict) or isinstance(data, list):
            if path_tokens[i] in data:
                data = data[path_tokens[i]]
            else:
                raise KeyError("/".join(path_tokens[0:i]))
        else:
            if i != len(path_tokens) - 1:
                raise KeyError("/".join(path_tokens[0:i]))
            data = data[path_tokens[i]]
    return data


# NOTE(mikal): this alias is to stop old style vendordata plugins from breaking
# post refactor. It should be removed when we finish deprecating those plugins.
VendorDataDriver = vendordata.VendorDataDriver
