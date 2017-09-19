# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Handles all requests relating to volumes + cinder.
"""

import collections
import copy
import functools
import sys

from cinderclient import api_versions as cinder_api_versions
from cinderclient import client as cinder_client
from cinderclient import exceptions as cinder_exception
from keystoneauth1 import exceptions as keystone_exception
from keystoneauth1 import loading as ks_loading
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import excutils
from oslo_utils import strutils
import six

from mogan.common import exception
from mogan.common.i18n import _
import mogan.conf
from mogan.conf import CONF
from mogan import service_auth

LOG = logging.getLogger(__name__)

_SESSION = None
CINDER_VOLUME_IN_USE = 'in-use'
CINDER_VOLUME_AVAILABLE = 'available'
CINDER_VOLUME_ATTACHED = 'attached'
CINDER_VOLUME_DETACHED = 'detached'
CINDER_VOLUME_CREATING = 'creating'


def reset_globals():
    """Testing method to reset globals.
    """
    global _SESSION
    _SESSION = None


def _check_microversion(url, microversion):
    """Checks to see if the requested microversion is supported by the current
    version of python-cinderclient and the volume API endpoint.

    :param url: Cinder API endpoint URL.
    :param microversion: Requested microversion. If not available at the given
        API endpoint URL, a CinderAPIVersionNotAvailable exception is raised.
    :returns: The microversion if it is available. This can be used to
        construct the cinder v3 client object.
    :raises: CinderAPIVersionNotAvailable if the microversion is not available.
    """
    max_api_version = cinder_client.get_highest_client_server_version(url)
    # get_highest_client_server_version returns a float which we need to cast
    # to a str and create an APIVersion object to do our version comparison.
    max_api_version = cinder_api_versions.APIVersion(str(max_api_version))
    # Check if the max_api_version matches the requested minimum microversion.
    if max_api_version.matches(microversion):
        # The requested microversion is supported by the client and the server.
        return microversion
    raise exception.CinderAPIVersionNotAvailable(version=microversion)


def cinderclient(context, microversion=None, skip_version_check=False):
    """Constructs a cinder client object for making API requests.

    :param context: The nova request context for auth.
    :param microversion: Optional microversion to check against the client.
        This implies that Cinder v3 is required for any calls that require a
        microversion. If the microversion is not available, this method will
        raise an CinderAPIVersionNotAvailable exception.
    :param skip_version_check: If True and a specific microversion is
        requested, the version discovery check is skipped and the microversion
        is used directly. This should only be used if a previous check for the
        same microversion was successful.
    """
    global _SESSION

    if not _SESSION:
        _SESSION = ks_loading.load_session_from_conf_options(
            CONF, mogan.conf.cinder.cinder_group.name)

    url = None
    endpoint_override = None

    auth = service_auth.get_auth_plugin(context)
    service_type, service_name, interface = CONF.cinder.catalog_info.split(':')

    service_parameters = {'service_type': service_type,
                          'service_name': service_name,
                          'interface': interface,
                          'region_name': CONF.cinder.os_region_name}

    if CONF.cinder.endpoint_template:
        url = CONF.cinder.endpoint_template % context.to_dict()
        endpoint_override = url
    else:
        url = _SESSION.get_endpoint(auth, **service_parameters)

    # TODO(jamielennox): This should be using proper version discovery from
    # the cinder service rather than just inspecting the URL for certain string
    # values.
    version = cinder_client.get_volume_api_from_url(url)

    if version == '1':
        raise exception.UnsupportedCinderAPIVersion(version=version)

    if version == '2':
        if microversion is not None:
            # The Cinder v2 API does not support microversions.
            raise exception.CinderAPIVersionNotAvailable(version=microversion)
        LOG.warning("The support for the Cinder API v2 is deprecated, please "
                    "upgrade to Cinder API v3.")

    if version == '3':
        version = '3.0'
        # Check to see a specific microversion is requested and if so, can it
        # be handled by the backing server.
        if microversion is not None:
            if skip_version_check:
                version = microversion
            else:
                version = _check_microversion(url, microversion)

    return cinder_client.Client(version,
                                session=_SESSION,
                                auth=auth,
                                endpoint_override=endpoint_override,
                                connect_retries=CONF.cinder.http_retries,
                                global_request_id=context.global_id,
                                **service_parameters)


def _untranslate_volume_summary_view(context, vol):
    """Maps keys for volumes summary view."""
    data = {}
    data['id'] = vol.id
    data['status'] = vol.status
    data['size'] = vol.size
    data['availability_zone'] = vol.availability_zone
    data['created_at'] = vol.created_at

    # TODO(jdg): The calling code expects attach_time and
    #            mountpoint to be set. When the calling
    #            code is more defensive this can be
    #            removed.
    data['attach_time'] = ""
    data['mountpoint'] = ""
    data['multiattach'] = getattr(vol, 'multiattach', False)

    if vol.attachments:
        data['attachments'] = collections.OrderedDict()
        for attachment in vol.attachments:
            a = {attachment['server_id']:
                 {'attachment_id': attachment.get('attachment_id'),
                  'mountpoint': attachment.get('device')}
                 }
            data['attachments'].update(a.items())

        data['attach_status'] = CINDER_VOLUME_ATTACHED
    else:
        data['attach_status'] = CINDER_VOLUME_DETACHED
    data['display_name'] = vol.name
    data['display_description'] = vol.description
    # TODO(jdg): Information may be lost in this translation
    data['volume_type_id'] = vol.volume_type
    data['snapshot_id'] = vol.snapshot_id
    data['bootable'] = strutils.bool_from_string(vol.bootable)
    data['volume_metadata'] = {}
    for key, value in vol.metadata.items():
        data['volume_metadata'][key] = value

    if hasattr(vol, 'volume_image_metadata'):
        volume_image_metadata = copy.deepcopy(vol.volume_image_metadata)
        data['volume_image_metadata'] = volume_image_metadata

    return data


def translate_cinder_exception(method):
    """Transforms a cinder exception but keeps its traceback intact."""
    @functools.wraps(method)
    def wrapper(self, ctx, *args, **kwargs):
        try:
            res = method(self, ctx, *args, **kwargs)
        except (cinder_exception.ConnectionError,
                keystone_exception.ConnectionError) as exc:
            err_msg = encodeutils.exception_to_unicode(exc)
            _reraise(exception.CinderConnectionFailed(reason=err_msg))
        except (keystone_exception.BadRequest,
                cinder_exception.BadRequest) as exc:
            err_msg = encodeutils.exception_to_unicode(exc)
            _reraise(exception.InvalidInput(reason=err_msg))
        except (keystone_exception.Forbidden,
                cinder_exception.Forbidden) as exc:
            err_msg = encodeutils.exception_to_unicode(exc)
            _reraise(exception.Forbidden(err_msg))
        return res
    return wrapper


def translate_volume_exception(method):
    """Transforms the exception for the volume but keeps its traceback intact.
    """
    def wrapper(self, ctx, volume_id, *args, **kwargs):
        try:
            res = method(self, ctx, volume_id, *args, **kwargs)
        except (keystone_exception.NotFound, cinder_exception.NotFound):
            _reraise(exception.VolumeNotFound(volume_id=volume_id))
        except cinder_exception.OverLimit as e:
            _reraise(exception.OverQuota(message=e.message))
        return res
    return translate_cinder_exception(wrapper)


def _reraise(desired_exc):
    six.reraise(type(desired_exc), desired_exc, sys.exc_info()[2])


class API(object):
    """API for interacting with the volume manager."""

    @translate_volume_exception
    def get(self, context, volume_id):
        item = cinderclient(context).volumes.get(volume_id)
        return _untranslate_volume_summary_view(context, item)

    @translate_cinder_exception
    def get_all(self, context, search_opts=None):
        search_opts = search_opts or {}
        items = cinderclient(context).volumes.list(detailed=True,
                                                   search_opts=search_opts)

        rval = []

        for item in items:
            rval.append(_untranslate_volume_summary_view(context, item))

        return rval

    def check_attached(self, context, volume):
        if volume['status'] != CINDER_VOLUME_IN_USE:
            msg = _("volume '%(vol)s' status must be 'in-use'. Currently in "
                    "'%(status)s' status") % {"vol": volume['id'],
                                              "status": volume['status']}
            raise exception.InvalidVolume(reason=msg)

    def check_detach(self, context, volume, instance=None):
        # TODO(vish): abstract status checking?
        if volume['status'] == CINDER_VOLUME_AVAILABLE:
            msg = _("volume %s already detached") % volume['id']
            raise exception.InvalidVolume(reason=msg)

        if volume['attach_status'] == CINDER_VOLUME_DETACHED:
            msg = _("Volume must be attached in order to detach.")
            raise exception.InvalidVolume(reason=msg)

        # NOTE(ildikov):Preparation for multiattach support, when a volume
        # can be attached to multiple hosts and/or instances,
        # so just check the attachment specific to this instance
        if instance is not None and instance.uuid not in volume['attachments']:
            # TODO(ildikov): change it to a better exception, when enable
            # multi-attach.
            raise exception.VolumeUnattached(volume_id=volume['id'])

    @translate_volume_exception
    def reserve_volume(self, context, volume_id):
        cinderclient(context).volumes.reserve(volume_id)

    @translate_volume_exception
    def unreserve_volume(self, context, volume_id):
        cinderclient(context).volumes.unreserve(volume_id)

    @translate_volume_exception
    def begin_detaching(self, context, volume_id):
        cinderclient(context).volumes.begin_detaching(volume_id)

    @translate_volume_exception
    def roll_detaching(self, context, volume_id):
        cinderclient(context).volumes.roll_detaching(volume_id)

    @translate_volume_exception
    def attach(self, context, volume_id, instance_uuid, mountpoint, mode='rw'):
        cinderclient(context).volumes.attach(volume_id, instance_uuid,
                                             mountpoint, mode=mode)

    @translate_volume_exception
    def detach(self, context, volume_id, instance_uuid=None,
               attachment_id=None):
        client = cinderclient(context)
        if attachment_id is None:
            volume = self.get(context, volume_id)
            if volume['multiattach']:
                attachments = volume.get('attachments', {})
                if instance_uuid:
                    attachment = attachments.get(instance_uuid, {})
                    attachment_id = attachment.get('attachment_id')
                    if not attachment_id:
                        LOG.warning(("attachment_id couldn't be retrieved "
                                     "for volume %(volume_id)s with "
                                     "instance_uuid %(instance_id)s. The "
                                     "volume has the 'multiattach' flag "
                                     "enabled, without the attachment_id "
                                     "Cinder most probably cannot perform "
                                     "the detach."),
                                    {'volume_id': volume_id,
                                     'instance_id': instance_uuid})
                else:
                    LOG.warning(("attachment_id couldn't be retrieved for "
                                 "volume %(volume_id)s. The volume has the "
                                 "'multiattach' flag enabled, without the "
                                 "attachment_id Cinder most probably "
                                 "cannot perform the detach."),
                                {'volume_id': volume_id})

        client.volumes.detach(volume_id, attachment_id)

    @translate_volume_exception
    def initialize_connection(self, context, volume_id, connector):
        try:
            connection_info = cinderclient(
                context).volumes.initialize_connection(volume_id, connector)
            connection_info['connector'] = connector
            return connection_info
        except cinder_exception.ClientException as ex:
            with excutils.save_and_reraise_exception():
                LOG.error(('Initialize connection failed for volume '
                           '%(vol)s on host %(host)s. Error: %(msg)s '
                           'Code: %(code)s. Attempting to terminate '
                           'connection.'),
                          {'vol': volume_id,
                           'host': connector.get('host'),
                           'msg': six.text_type(ex),
                           'code': ex.code})
                try:
                    self.terminate_connection(context, volume_id, connector)
                except Exception as exc:
                    code = exc.code if hasattr(exc, 'code') else None
                    LOG.error(('Connection between volume %(vol)s and host '
                               '%(host)s might have succeeded, but attempt '
                               'to terminate connection has failed. '
                               'Validate the connection and determine if '
                               'manual cleanup is needed. Error: %(msg)s '
                               'Code: %(code)s.'),
                              {'vol': volume_id,
                               'host': connector.get('host'),
                               'msg': six.text_type(exc),
                               'code': code})

    @translate_volume_exception
    def terminate_connection(self, context, volume_id, connector):
        return cinderclient(context).volumes.terminate_connection(volume_id,
                                                                  connector)

    @translate_volume_exception
    def create(self, context, size, name, description, snapshot=None,
               image_id=None, volume_type=None, metadata=None,
               availability_zone=None):
        client = cinderclient(context)

        if snapshot is not None:
            snapshot_id = snapshot['id']
        else:
            snapshot_id = None

        kwargs = dict(snapshot_id=snapshot_id,
                      volume_type=volume_type,
                      user_id=context.user_id,
                      project_id=context.project_id,
                      availability_zone=availability_zone,
                      metadata=metadata,
                      imageRef=image_id,
                      name=name,
                      description=description)

        item = client.volumes.create(size, **kwargs)
        return _untranslate_volume_summary_view(context, item)

    @translate_volume_exception
    def delete(self, context, volume_id):
        cinderclient(context).volumes.delete(volume_id)
