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
from oslo_utils import timeutils


OCATA = '2017-02-22'

OPENSTACK_VERSIONS = [
    OCATA,
]

VERSION = "version"
MD_JSON_NAME = "meta_data.json"

LOG = logging.getLogger(__name__)


class InvalidMetadataVersion(Exception):
    pass


class InvalidMetadataPath(Exception):
    pass


class InstanceMetadata(object):
    """Instance metadata."""

    def __init__(self, instance, extra_md=None):
        """Creation of this object should basically cover all time consuming
        collection.  Methods after that should not cause time delays due to
        network operations or lengthy cpu operations.

        The user should then get a single instance and make multiple method
        calls on it.
        """

        self.instance = instance
        self.extra_md = extra_md
        self.availability_zone = instance.availability_zone
        # TODO(zhenguo): Add hostname to instance object
        self.hostname = instance.name
        self.uuid = instance.uuid
        self.files = []

        self.route_configuration = None

    def _route_configuration(self):
        if self.route_configuration:
            return self.route_configuration

        path_handlers = {MD_JSON_NAME: self._metadata_as_json}

        self.route_configuration = RouteConfiguration(path_handlers)
        return self.route_configuration

    def get_openstack_item(self, path_tokens):
        return self._route_configuration().handle_path(path_tokens)

    def _metadata_as_json(self, version, path):
        metadata = {'uuid': self.uuid}
        if self.extra_md:
            metadata.update(self.extra_md)

        metadata['hostname'] = self.hostname
        metadata['name'] = self.instance.name
        metadata['availability_zone'] = self.availability_zone

        return jsonutils.dump_as_bytes(metadata)

    def lookup(self, path):
        if path == "" or path[0] != "/":
            path = posixpath.normpath("/" + path)
        else:
            path = posixpath.normpath(path)

        # fix up requests, prepending /openstack to anything that does
        # not match
        path_tokens = path.split('/')[1:]
        if path_tokens[0] not in ("openstack"):
            if path_tokens[0] == "":
                # request for /
                path_tokens = ["openstack"]
            else:
                path_tokens = ["openstack"] + path_tokens
            path = "/" + "/".join(path_tokens)

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
            return versions

        try:
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
