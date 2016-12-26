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

import posixpath

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import importutils
from oslo_utils import timeutils
import six

from mogan.api.metadata import password
from mogan.api.metadata import vendordata
from mogan.api.metadata import vendordata_dynamic
from mogan.api.metadata import vendordata_json
from mogan.common.i18n import _LW
from mogan.common import utils
import mogan.conf
from mogan.engine import netutils


CONF = mogan.conf.CONF

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
NEWTON = '2016-10-06'
# TODO(Shaohe): Need to suppport these features in Z_TBD release.
Z_TBD = '2100-10-06'

OPENSTACK_VERSIONS = [
    NEWTON,
    Z_TBD
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
        # TODO(Shaohe): userdata and keypairs are in support list.
        if not content:
            content = []

        # ctxt = context.get_admin_context()

        # The default value of mimeType is set to MIME_TYPE_TEXT_PLAIN
        self.set_mimetype(MIME_TYPE_TEXT_PLAIN)
        self.instance = instance
        self.extra_md = extra_md

        self.availability_zone = instance.availability_zone
        # will support later
        self.security_groups = None

        # TODO(Shaohe) will support user_data in future.
        self.userdata_raw = None

        self.address = address

        # expose instance metadata is not supported at present.
        self.launch_metadata = {}

        self.password = password.extract_password(extra_md.get("admin_pass"))

        self.uuid = instance.uuid

        self.content = {}
        self.files = []

        # get network info, and the rendered network template
        if network_info is None:
            network_info = instance.network_info

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
            self.network_config = {
                "name": "network_config",
                'content_path': "/%s/%s" % (CONTENT_DIR, key)}

        # 'content' is passed in from the configdrive code in
        # mogan/engine/baremetal/ironic.py.  That's how we get the injected
        # files (personalities) in. AFAIK they're not stored in the db at all,
        # so are not available later (web service metadata time).
        for (path, contents) in content:
            key = "%04i" % len(self.content)
            self.files.append(
                {'path': path,
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
        # FIXME(Shaohe): launch_metadata is in plan.
        if self.launch_metadata:
            LOG.warning(_LW('Please fix me for this feature: '
                            '%s'), "launch_metadata", instance=self.instance)
            metadata['meta'] = self.launch_metadata
        if self.files:
            metadata['files'] = self.files
        if self.extra_md:
            metadata.update(self.extra_md)
        if self.network_config:
            metadata['network_config'] = self.network_config

        metadata['hostname'] = self._get_hostname()
        # FIXME(Shaohe): mogan do not support display_name at present. Just use
        # instance.name
        metadata['name'] = self.instance.name
        metadata['availability_zone'] = self.availability_zone
        metadata['project_id'] = self.instance.project_id
        # TODO(Shaohe): need to support launch_index for the order of booting
        # instance especially in multi-instance scenario
        # need to support 'random_seed', 'devices'

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
        ret = [MD_JSON_NAME, PASS_NAME]
        if self.userdata_raw is not None:
            ret.append(UD_NAME)
        if self._check_os_version(Z_TBD, version):
            ret.append(VD_JSON_NAME)
        if self._check_os_version(Z_TBD, version):
            ret.append(NW_JSON_NAME)
        if self._check_os_version(NEWTON, version):
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
        return password.handle_password

    def _vendor_data(self, version, path):
        # FIXME(Shaohe): need to remove this condition.
        if not self._check_os_version(Z_TBD, version):
            LOG.warning(_LW('Please fix me for this feature: '
                            '%s'), "_vendor_data", instance=self.instance)
            return "{}"
        if self._check_os_version(Z_TBD, version):
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
        if self._check_os_version(NEWTON, version):
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
        # FIXME(Shaohe): After we support all the related features, remove
        # this condition.
        if required == Z_TBD:
            LOG.warning(_LW('Please remove this condition in function: '
                            '%s'), "_check_version", instance=self.instance)
            return False
        return versions.index(requested) >= versions.index(required)

    def _check_os_version(self, required, requested):
        return self._check_version(required, requested, OPENSTACK_VERSIONS)

    def _get_hostname(self):
        # NOTE(Shaohe): Do not support dhcp_domain, we can add it if necessary.
        # FIXME(Shaohe): We can add a "hostname" attr for instance. and move it
        # to up layer. also support some strategy to generate "hostname". Nova
        # can use name_template to generate "hostname" for multi-instances.
        default_hostname = "Server-" + self.instance.uuid
        utils.sanitize_hostname(default_hostname)

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

            if self._check_version(Z_TBD, version, ALL_OPENSTACK_VERSIONS):
                path = 'openstack/%s/%s' % (version, UD_NAME)
                yield (path, self.lookup(path))

            path = 'openstack/%s/%s' % (version, VD_JSON_NAME)
            yield (path, self.lookup(path))

            if self._check_version(Z_TBD, version, ALL_OPENSTACK_VERSIONS):
                path = 'openstack/%s/%s' % (version, NW_JSON_NAME)
                yield (path, self.lookup(path))

            if self._check_version(Z_TBD, version,
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
