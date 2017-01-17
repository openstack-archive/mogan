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

from neutronclient.common import exceptions as neutron_exceptions
from neutronclient.v2_0 import client as clientv20
from oslo_log import log as logging

from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import keystone
from mogan.conf import CONF

LOG = logging.getLogger(__name__)

_NEUTRON_SESSION = None


def _get_neutron_session():
    global _NEUTRON_SESSION
    if not _NEUTRON_SESSION:
        _NEUTRON_SESSION = keystone.get_session('neutron')
    return _NEUTRON_SESSION


def get_client(token=None):
    params = {'retries': CONF.neutron.retries}
    url = CONF.neutron.url
    session = _get_neutron_session()
    if token is None:
        params['session'] = session
        # NOTE(pas-ha) endpoint_override==None will auto-discover
        # endpoint from Keystone catalog.
        # Region is needed only in this case.
        # SSL related options are ignored as they are already embedded
        # in keystoneauth Session object
        if url:
            params['endpoint_override'] = url
        else:
            params['region_name'] = CONF.keystone.region_name
    else:
        params['token'] = token
        params['endpoint_url'] = url or keystone.get_service_url(
            session, service_type='network')
        params.update({
            'timeout': CONF.neutron.url_timeout,
            'insecure': CONF.neutron.insecure,
            'ca_cert': CONF.neutron.cafile})

    return clientv20.Client(**params)


def _ensure_requested_network_ordering(accessor, unordered, preferred):
    """Sort a list with respect to the preferred network ordering."""
    if preferred:
        unordered.sort(key=lambda i: preferred.index(accessor(i)))


class API(object):
    """API for interacting with the neutron 2.x API."""

    def create_port(self, context, network_uuid, mac, instance_uuid):
        """Create neutron port."""

        client = get_client(context.auth_token)
        body = {
            'port': {
                'network_id': network_uuid,
                'mac_address': mac,
            }
        }

        try:
            port = client.create_port(body)
        except neutron_exceptions.NeutronClientException as e:
            msg = (_("Could not create neutron port on network %(net)s for "
                     "instance %(instance)s. %(exc)s"),
                   {'net': network_uuid, 'instance': instance_uuid, 'exc': e})
            LOG.exception(msg)
            raise exception.NetworkError(msg)
        return port

    def delete_port(self, context, port_id, instance_uuid):
        """Delete neutron port."""

        client = get_client(context.auth_token)
        try:
            client.delete_port(port_id)
        except neutron_exceptions.NeutronClientException as e:
            msg = (_('Could not remove VIF %(vif)s of instance %(instance)s, '
                     'possibly a network issue: %(exc)s') %
                   {'vif': port_id, 'instance': instance_uuid, 'exc': e})
            LOG.exception(msg)
            raise exception.NetworkError(msg)

    def validate_networks(self, context, requested_networks, num_instances):
        """Validate that the tenant can use the requested networks.

        Return the number of instances than can be successfully allocated
        with the requested network configuration.
        """
        LOG.debug('validate_networks() for %s', requested_networks)
        # TODO(little): check the network port number and return the actual
        # num_instances

        return num_instances
