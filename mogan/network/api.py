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
from oslo_utils import excutils

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


class API(object):
    """API for interacting with the neutron 2.x API."""

    def create_port(self, context, network_uuid, mac, instance_uuid):
        """Create neutron port."""

        client = get_client(context.auth_token)
        body = {
            'port': {
                'network_id': network_uuid,
                'mac_address': mac,
                'device_id': instance_uuid,
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

    def _show_port(self, client, port_id):
        """Return the port for the client given the port id."""

        try:
            result = client.show_port(port_id)
            return result.get('port')
        except neutron_exceptions.PortNotFoundClient:
            raise exception.PortNotFound(port_id=port_id)
        except neutron_exceptions.Unauthorized:
            raise exception.Forbidden()
        except neutron_exceptions.NeutronClientException as e:
            msg = (_("Failed to access port %(port_id)s: %(reason)s") %
                   {'port_id': port_id, 'reason': e})
            raise exception.NetworkError(msg)

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

    def _safe_get_floating_ips(self, client, **kwargs):
        """Get floating IP gracefully handling 404 from Neutron."""
        try:
            return client.list_floatingips(**kwargs)['floatingips']
        # If a neutron plugin does not implement the L3 API a 404 from
        # list_floatingips will be raised.
        except neutron_exceptions.NotFound:
            return []
        except neutron_exceptions.NeutronClientException as e:
            # bug/1513879 neutron client is currently using
            # NeutronClientException when there is no L3 API
            if e.status_code == 404:
                return []
            with excutils.save_and_reraise_exception():
                LOG.exception('Unable to access floating IP for %s',
                              ', '.join(['%s %s' % (k, v)
                                         for k, v in kwargs.items()]))

    def _get_floating_ip_by_address(self, client, address):
        """Get floating IP from floating IP address."""
        if not address:
            raise exception.FloatingIpNotFoundForAddress(address=address)
        fips = self._safe_get_floating_ips(client, floating_ip_address=address)
        if len(fips) == 0:
            raise exception.FloatingIpNotFoundForAddress(address=address)
        elif len(fips) > 1:
            raise exception.FloatingIpMultipleFoundForAddress(address=address)
        return fips[0]

    def get_floating_ip_by_address(self, context, address):
        """Return a floating IP given an address."""
        client = get_client(context.auth_token)
        fip = self._get_floating_ip_by_address(client, address)
        return fip

    def get_instance_id_by_floating_address(self, context, address):
        """Return the instance id a floating IP's fixed IP is allocated to."""
        client = get_client(context.auth_token)
        fip = self._get_floating_ip_by_address(client, address)
        if not fip['port_id']:
            return None

        try:
            port = self._show_port(client, fip['port_id'])
        except exception.PortNotFound:
            # NOTE: Here is a potential race condition between _show_port() and
            # _get_floating_ip_by_address(). fip['port_id'] shows a port which
            # is the server instance's. At _get_floating_ip_by_address(),
            # Neutron returns the list which includes the instance. Just after
            # that, the deletion of the instance happens and Neutron returns
            # 404 on _show_port().
            LOG.debug('The port(%s) is not found', fip['port_id'])
            return None

        return port['device_id']

    def associate_floating_ip(self, context, floating_address,
                              port_id, fixed_address):
        """Associate a floating IP with a fixed IP."""

        client = get_client(context.auth_token)
        fip = self._get_floating_ip_by_address(client, floating_address)
        param = {'port_id': port_id,
                 'fixed_ip_address': fixed_address}
        client.update_floatingip(fip['id'], {'floatingip': param})

    def disassociate_floating_ip(self, context, address):
        """Disassociate a floating IP from the instance."""

        client = get_client(context.auth_token)
        fip = self._get_floating_ip_by_address(client, address)
        client.update_floatingip(fip['id'], {'floatingip': {'port_id': None}})

    def _get_available_networks(self, context, project_id,
                                net_ids, client):
        """Return a network list available for the tenant."""

        # This search will also include 'shared' networks.
        search_opts = {'id': net_ids}
        nets = client.list_networks(**search_opts).get('networks', [])

        _ensure_requested_network_ordering(
            lambda x: x['id'],
            nets,
            net_ids)

        return nets

    def _ports_needed_per_instance(self, context, client, requested_networks):

        ports_needed_per_instance = 0
        net_ids_requested = []
        for request in requested_networks:
            ports_needed_per_instance += 1
            net_ids_requested.append(request['net_id'])

        # Now check to see if all requested networks exist
        if net_ids_requested:
            nets = self._get_available_networks(
                context, context.project_id, net_ids_requested,
                client)

            for net in nets:
                if not net.get('subnets'):
                    raise exception.NetworkRequiresSubnet(
                        network_uuid=net['id'])

            if len(nets) != len(net_ids_requested):
                requested_netid_set = set(net_ids_requested)
                returned_netid_set = set([net['id'] for net in nets])
                lostid_set = requested_netid_set - returned_netid_set
                if lostid_set:
                    id_str = ''
                    for _id in lostid_set:
                        id_str = id_str and id_str + ', ' + _id or _id
                    raise exception.NetworkNotFound(network_id=id_str)

        return ports_needed_per_instance

    def validate_networks(self, context, requested_networks, num_instances):
        """Validate that the tenant can use the requested networks.

        Return the number of instances than can be successfully allocated
        with the requested network configuration.
        """
        LOG.debug('validate_networks() for %s', requested_networks)

        client = get_client(context.auth_token)
        ports_needed_per_instance = self._ports_needed_per_instance(
            context, client, requested_networks)

        # Check the quota and return how many of the requested number of
        # instances can be created
        if ports_needed_per_instance:
            quotas = client.show_quota(context.project_id)['quota']
            if quotas.get('port', -1) == -1:
                # Unlimited Port Quota
                return num_instances

            # We only need the port count so only ask for ids back.
            params = dict(tenant_id=context.project_id, fields=['id'])
            ports = client.list_ports(**params)['ports']
            free_ports = quotas.get('port') - len(ports)
            if free_ports < 0:
                msg = (_("The number of defined ports: %(ports)d "
                         "is over the limit: %(quota)d") %
                       {'ports': len(ports),
                        'quota': quotas.get('port')})
                raise exception.PortLimitExceeded(msg)
            ports_needed = ports_needed_per_instance * num_instances
            if free_ports >= ports_needed:
                return num_instances
            else:
                return free_ports // ports_needed_per_instance

        return num_instances


def _ensure_requested_network_ordering(accessor, unordered, preferred):
    """Sort a list with respect to the preferred network ordering."""
    if preferred:
        unordered.sort(key=lambda i: preferred.index(accessor(i)))
