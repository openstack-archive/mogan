# Copyright 2010 OpenStack Foundation
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

"""Implementation of an image service that uses Glance as the backend."""

import copy
import inspect
import itertools
import random
import sys
import time

import glanceclient
import glanceclient.exc
from glanceclient.v2 import schemas
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six
from six.moves import range

from nimble.common import exception
from nimble.common.i18n import _LE
from nimble import conf

LOG = logging.getLogger(__name__)
CONF = conf.CONF


def generate_identity_headers(context, status='Confirmed'):
    return {
        'X-Auth-Token': getattr(context, 'auth_token', None),
        'X-User-Id': getattr(context, 'user', None),
        'X-Tenant-Id': getattr(context, 'tenant', None),
        'X-Roles': ','.join(getattr(context, 'roles', [])),
        'X-Identity-Status': status,
    }


def _glanceclient_from_endpoint(context, endpoint, version=2):
    """Instantiate a new glanceclient.Client object."""
    params = {}
    # NOTE(sdague): even if we aren't using keystone, it doesn't
    # hurt to send these headers.
    params['identity_headers'] = generate_identity_headers(context)
    if endpoint.startswith('https://'):
        # https specific params
        params['insecure'] = CONF.glance.glance_api_insecure
        params['ssl_compression'] = False
        if CONF.glance.glance_cafile:
            params['cacert'] = CONF.glance.glance_cafile
    return glanceclient.Client(str(version), endpoint, **params)


def get_api_servers():
    """Shuffle a list of CONF.glance.glance_api_servers and return an
    iterator that will cycle through the list, looping around to the
    beginning if necessary.
    """
    api_servers = []

    for api_server in CONF.glance.glance_api_servers:
        if '//' not in api_server:
            api_server = 'http://' + api_server
        api_servers.append(api_server)
    random.shuffle(api_servers)
    return itertools.cycle(api_servers)


class GlanceClientWrapper(object):
    """Glance client wrapper class that implements retries."""

    def __init__(self, context=None, endpoint=None):
        if endpoint is not None:
            self.client = self._create_static_client(context,
                                                     endpoint,
                                                     2)
        else:
            self.client = None
        self.api_servers = None

    def _create_static_client(self, context, endpoint, version):
        """Create a client that we'll use for every call."""
        self.api_server = str(endpoint)
        return _glanceclient_from_endpoint(context, endpoint, version)

    def _create_onetime_client(self, context, version):
        """Create a client that will be used for one call."""
        if self.api_servers is None:
            self.api_servers = get_api_servers()
        self.api_server = next(self.api_servers)
        return _glanceclient_from_endpoint(context, self.api_server, version)

    def call(self, context, version, method, *args, **kwargs):
        """Call a glance client method.  If we get a connection error,
        retry the request according to CONF.glance.glance_num_retries.
        """
        retry_excs = (glanceclient.exc.ServiceUnavailable,
                      glanceclient.exc.InvalidEndpoint,
                      glanceclient.exc.CommunicationError)
        num_attempts = 1 + CONF.glance.glance_num_retries

        for attempt in range(1, num_attempts + 1):
            client = self.client or self._create_onetime_client(context,
                                                                version)
            try:
                controller = getattr(client,
                                     kwargs.pop('controller', 'images'))
                result = getattr(controller, method)(*args, **kwargs)
                if inspect.isgenerator(result):
                    # Convert generator results to a list, so that we can
                    # catch any potential exceptions now and retry the call.
                    return list(result)
                return result
            except retry_excs as e:
                if attempt < num_attempts:
                    extra = "retrying"
                else:
                    extra = 'done trying'

                LOG.exception(_LE("Error contacting glance server "
                                  "'%(server)s' for '%(method)s', "
                                  "%(extra)s."),
                              {'server': self.api_server,
                               'method': method, 'extra': extra})
                if attempt == num_attempts:
                    raise exception.GlanceConnectionFailed(
                        server=str(self.api_server), reason=six.text_type(e))
                time.sleep(1)


class GlanceImageServiceV2(object):
    """Provides storage and retrieval of disk image objects within Glance."""

    def __init__(self, client=None):
        self._client = client or GlanceClientWrapper()

    def show(self, context, image_id):
        """Returns a dict with image data for the given opaque image id.

        :param context: The context object to pass to image client
        :param image_id: The UUID of the image
        """
        try:
            image = self._client.call(context, 2, 'get', image_id)
        except Exception:
            _reraise_translated_image_exception(image_id)

        image = _translate_from_glance(image)

        return image


def _translate_from_glance(image, include_locations=False):
    image_meta = _extract_attributes(
        image, include_locations=include_locations)

    image_meta = _convert_timestamps_to_datetimes(image_meta)
    image_meta = _convert_from_string(image_meta)
    return image_meta


def _convert_timestamps_to_datetimes(image_meta):
    """Returns image with timestamp fields converted to datetime objects."""
    for attr in ['created_at', 'updated_at', 'deleted_at']:
        if image_meta.get(attr):
            image_meta[attr] = timeutils.parse_isotime(image_meta[attr])
    return image_meta


# NOTE(bcwaldon): used to store non-string data in glance metadata
def _json_loads(properties, attr):
    prop = properties[attr]
    if isinstance(prop, six.string_types):
        properties[attr] = jsonutils.loads(prop)


def _json_dumps(properties, attr):
    prop = properties[attr]
    if not isinstance(prop, six.string_types):
        properties[attr] = jsonutils.dumps(prop)


_CONVERT_PROPS = ('block_device_mapping', 'mappings')


def _convert(method, metadata):
    metadata = copy.deepcopy(metadata)
    properties = metadata.get('properties')
    if properties:
        for attr in _CONVERT_PROPS:
            if attr in properties:
                method(properties, attr)

    return metadata


def _convert_from_string(metadata):
    return _convert(_json_loads, metadata)


def _extract_attributes(image, include_locations=False):
    include_locations_attrs = ['direct_url', 'locations']
    omit_attrs = ['self', 'schema', 'protected', 'virtual_size', 'file',
                  'tags']
    raw_schema = image.schema
    schema = schemas.Schema(raw_schema)
    output = {'properties': {}, 'deleted': False, 'deleted_at': None,
              'disk_format': None, 'container_format': None, 'name': None,
              'checksum': None}
    for name, value in image.items():
        if (name in omit_attrs
                or name in include_locations_attrs and not include_locations):
            continue
        elif name == 'visibility':
            output['is_public'] = value == 'public'
        elif name == 'size' and value is None:
            output['size'] = 0
        elif schema.is_base_property(name):
            output[name] = value
        else:
            output['properties'][name] = value

    return output


def _reraise_translated_image_exception(image_id):
    """Transform the exception for the image but keep its traceback intact."""
    exc_type, exc_value, exc_trace = sys.exc_info()
    new_exc = _translate_image_exception(image_id, exc_value)
    six.reraise(new_exc, None, exc_trace)


def _translate_image_exception(image_id, exc_value):
    if isinstance(exc_value, (glanceclient.exc.Forbidden,
                              glanceclient.exc.Unauthorized)):
        return exception.ImageNotAuthorized(image_id=image_id)
    if isinstance(exc_value, glanceclient.exc.NotFound):
        return exception.ImageNotFound(image_id=image_id)
    if isinstance(exc_value, glanceclient.exc.BadRequest):
        return exception.ImageBadRequest(image_id=image_id,
                                         response=six.text_type(exc_value))
    return exc_value


def get_image_service(context):
    """Create an image_service."""
    return GlanceImageServiceV2()
