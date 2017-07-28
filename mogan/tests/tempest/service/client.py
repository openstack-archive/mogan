# Copyright 2014 OpenStack Foundation
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

from oslo_serialization import jsonutils as json
from tempest import config
from tempest.lib.common import rest_client
from tempest.lib.services.image.v2 import images_client as image_cli
from tempest.lib.services.network import floating_ips_client as fip_cli
from tempest.lib.services.network import networks_client as network_cli
from tempest import manager

CONF = config.CONF


class BaremetalComputeClient(rest_client.RestClient):
    version = '1'
    # TODO(liusheng) since the endpoints of Mogan includes '/v1',
    # here we shouldn't add this, may remove the 'v1' in endpoint urls
    # uri_prefix = "v1"
    uri_prefix = ""

    def deserialize(self, body):
        return json.loads(body.replace("\n", ""))

    def serialize(self, body):
        return json.dumps(body)

    def list_flavors(self):
        uri = '%s/flavors' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['flavors']
        return rest_client.ResponseBodyList(resp, body)

    def show_flavor(self, flavor_uuid):
        uri = '%s/flavors/%s' % (self.uri_prefix, flavor_uuid)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def delete_flavor(self, flavor_uuid):
        uri = "%s/flavors/%s" % (self.uri_prefix, flavor_uuid)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_flavor(self, **kwargs):
        uri = "%s/flavors" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_server(self, **kwargs):
        uri = "%s/servers" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def list_servers(self):
        uri = '%s/servers' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['servers']
        return rest_client.ResponseBodyList(resp, body)

    def show_server(self, server_id):
        uri = '%s/servers/%s' % (self.uri_prefix, server_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def delete_server(self, server_id):
        uri = "%s/servers/%s" % (self.uri_prefix, server_id)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_keypair(self, **kwargs):
        uri = "%s/keypairs" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def show_keypair(self, key_name, user_id=None):
        uri = "%s/keypairs/%s" % (self.uri_prefix, key_name)
        if user_id:
            uri = '%s?user_id=%s' % (uri, user_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def list_keypairs(self, user_id=None):
        uri = '%s/keypairs' % self.uri_prefix
        if user_id:
            uri = '%s?user_id=%s' % (uri, user_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['keypairs']
        return rest_client.ResponseBodyList(resp, body)

    def delete_keypair(self, key_name, user_id=None):
        uri = "%s/keypairs/%s" % (self.uri_prefix, key_name)
        if user_id:
            uri = '%s?user_id=%s' % (uri, user_id)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_get_state(self, server_id):
        uri = '%s/servers/%s/states' % (self.uri_prefix, server_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_set_power_state(self, server_id, target):
        uri = '%s/servers/%s/states/power' % (self.uri_prefix, server_id)
        target_body = {'target': target}
        target_body = self.serialize(target_body)
        resp, body = self.put(uri, target_body)
        self.expected_success(202, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_set_lock_state(self, server_id, target):
        uri = '%s/servers/%s/states/lock' % (self.uri_prefix, server_id)
        target_body = {'target': target}
        target_body = self.serialize(target_body)
        resp, body = self.put(uri, target_body)
        self.expected_success(202, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_set_provision_state(self, server_id, target):
        uri = '%s/servers/%s/states/provision' % (self.uri_prefix, server_id)
        target_body = {'target': target}
        target_body = self.serialize(target_body)
        resp, body = self.put(uri, target_body)
        if body:
            body = self.deserialize(body)
        self.expected_success(202, resp.status)
        return rest_client.ResponseBody(resp, body)

    def list_nodes(self):
        uri = '%s/nodes' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['nodes']
        return rest_client.ResponseBodyList(resp, body)

    def server_get_serial_console(self, server_id):
        uri = '%s/servers/%s/serial_console' % (self.uri_prefix, server_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['console']
        return rest_client.ResponseBody(resp, body)

    def server_get_networks(self, server_id):
        uri = '%s/servers/%s/networks' % (self.uri_prefix, server_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['nics']
        return rest_client.ResponseBodyList(resp, body)

    def server_attach_interface(self, server_id, net_id):
        uri = '%s/servers/%s/networks/interfaces' % (self.uri_prefix,
                                                     server_id)
        body = {"net_id": net_id}
        body = self.serialize(body)
        resp, body = self.post(uri, body)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_associate_floatingip(self, server_id, floatingip,
                                    fixed_ip=None):
        uri = '%s/servers/%s/networks/floatingips' % (
            self.uri_prefix, server_id)
        body = {"address": floatingip}
        if fixed_ip:
            body.update({'fixed_address': fixed_ip})
        body = self.serialize(body)
        resp, body = self.post(uri, body)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_disassociate_floatingip(self, server_id, floatingip):
        uri = '%s/servers/%s/networks/floatingips/%s' % (
            self.uri_prefix, server_id, floatingip)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def server_detach_interface(self, server_id, port_id):
        uri = '%s/servers/%s/networks/interfaces/%s' % (self.uri_prefix,
                                                        server_id, port_id)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def list_aggregates(self):
        uri = '%s/aggregates' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['aggregates']
        return rest_client.ResponseBodyList(resp, body)

    def show_aggregate(self, aggregate_uuid):
        uri = '%s/aggregates/%s' % (self.uri_prefix, aggregate_uuid)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def delete_aggregate(self, aggregate_uuid):
        uri = "%s/aggregates/%s" % (self.uri_prefix, aggregate_uuid)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_aggregate(self, **kwargs):
        uri = "%s/aggregates" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)


class BaremetalNodeClient(rest_client.RestClient):
    version = '1'
    uri_prefix = "v1"

    def deserialize(self, body):
        return json.loads(body.replace("\n", ""))

    def serialize(self, body):
        return json.dumps(body)

    def list_bm_nodes(self):
        uri = '%s/nodes' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['nodes']
        return rest_client.ResponseBodyList(resp, body)

    def show_bm_node(self, node_uuid=None, service_id=None):
        if service_id:
            uri = '%s/nodes/detail?instance_uuid=%s' % (self.uri_prefix,
                                                        service_id)
        else:
            uri = '%s/nodes/%s' % (self.uri_prefix, node_uuid)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        if service_id:
            body = body['nodes'][0]
        return rest_client.ResponseBody(resp, body)

    def set_node_console_state(self, node_id, enabled):
        uri = '%s/nodes/%s/states/console' % (self.uri_prefix, node_id)
        target_body = {'enabled': enabled}
        target_body = self.serialize(target_body)
        resp, body = self.put(uri, target_body)
        self.expected_success(202, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def get_node_console(self, node_id):
        uri = '%s/nodes/%s/states/console' % (self.uri_prefix, node_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def update_bm_node(self, node_id, updates):
        uri = '%s/nodes/%s' % (self.uri_prefix, node_id)
        target_body = self.serialize(updates)
        resp, body = self.patch(uri, target_body)
        self.expected_success(200, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def bm_node_set_console_port(self, node_id, port):
        updates = [{"path": "/driver_info/ipmi_terminal_port",
                    "value": port, "op": "add"}]
        self.update_bm_node(node_id, updates)


class BaremetalAggregateClient(rest_client.RestClient):
    version = '1'
    uri_prefix = "v1"

    def deserialize(self, body):
        return json.loads(body.replace("\n", ""))

    def serialize(self, body):
        return json.dumps(body)


class Manager(manager.Manager):

    load_clients = [
        'baremetal_compute_client',
        'networks_client',
        'image_client_v2',
        'baremetal_node_client',
        'network_floatingip_client'
    ]

    default_params = {
        'disable_ssl_certificate_validation':
            CONF.identity.disable_ssl_certificate_validation,
        'ca_certs': CONF.identity.ca_certificates_file,
        'trace_requests': CONF.debug.trace_requests
    }

    baremetal_compute_params = {
        'service': CONF.baremetal_compute_plugin.catalog_type,
        'region': CONF.identity.region,
        'endpoint_type': CONF.baremetal_compute_plugin.endpoint_type,
    }
    baremetal_compute_params.update(default_params)

    image_params = {
        'service': CONF.image.catalog_type,
        'region': CONF.image.region or CONF.identity.region,
        'endpoint_type': CONF.image.endpoint_type,
        'build_interval': CONF.image.build_interval,
        'build_timeout': CONF.image.build_timeout,
    }
    image_params.update(default_params)

    network_params = {
        'service': CONF.network.catalog_type,
        'region': CONF.network.region or CONF.identity.region,
        'endpoint_type': CONF.network.endpoint_type,
        'build_interval': CONF.network.build_interval,
        'build_timeout': CONF.network.build_timeout,
    }
    network_params.update(default_params)

    baremetal_node_params = {
        'service': CONF.baremetal_node_plugin.catalog_type,
        'region': CONF.identity.region,
        'endpoint_type': CONF.baremetal_node_plugin.endpoint_type,
    }
    baremetal_node_params.update(default_params)

    def __init__(self, credentials=None, service=None):
        super(Manager, self).__init__(credentials)
        for client in self.load_clients:
            getattr(self, 'set_%s' % client)()

    def set_baremetal_compute_client(self):
        self.baremetal_compute_client = BaremetalComputeClient(
            self.auth_provider, **self.baremetal_compute_params)

    def set_networks_client(self):
        self.networks_client = network_cli.NetworksClient(
            self.auth_provider,
            **self.network_params)

    def set_network_floatingip_client(self):
        self.network_floatingip_client = fip_cli.FloatingIPsClient(
            self.auth_provider,
            **self.network_params)

    def set_image_client_v2(self):
        self.image_client_v2 = image_cli.ImagesClient(
            self.auth_provider,
            **self.image_params)

    def set_baremetal_node_client(self):
        self.baremetal_node_client = BaremetalNodeClient(
            self.auth_provider,
            **self.baremetal_node_params)
