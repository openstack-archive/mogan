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
from tempest.lib.services.compute import networks_client as network_cli
from tempest.lib.services.image.v2 import images_client as image_cli
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

    def list_instance_types(self):
        uri = '%s/types' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['types']
        return rest_client.ResponseBodyList(resp, body)

    def show_instance_type(self, type_id):
        uri = '%s/types/%s' % (self.uri_prefix, type_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def delete_instance_type(self, type_id):
        uri = "%s/types/%s" % (self.uri_prefix, type_id)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_instance_type(self, **kwargs):
        uri = "%s/types" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def create_instance(self, **kwargs):
        uri = "%s/instances" % self.uri_prefix
        body = self.serialize(kwargs)
        resp, body = self.post(uri, body)
        self.expected_success(201, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def list_instances(self):
        uri = '%s/instances' % self.uri_prefix
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)['instances']
        return rest_client.ResponseBodyList(resp, body)

    def show_instance(self, instance_id):
        uri = '%s/instances/%s' % (self.uri_prefix, instance_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)

    def delete_instance(self, instance_id):
        uri = "%s/instances/%s" % (self.uri_prefix, instance_id)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        if body:
            body = self.deserialize(body)
        return rest_client.ResponseBody(resp, body)


class Manager(manager.Manager):

    load_clients = [
        'baremetal_compute_client',
        'compute_networks_client',
        'image_client_v2',
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

    compute_params = {
        'service': CONF.compute.catalog_type,
        'region': CONF.compute.region or CONF.identity.region,
        'endpoint_type': CONF.compute.endpoint_type,
        'build_interval': CONF.compute.build_interval,
        'build_timeout': CONF.compute.build_timeout,
    }
    compute_params.update(default_params)

    image_params = {
        'service': CONF.image.catalog_type,
        'region': CONF.image.region or CONF.identity.region,
        'endpoint_type': CONF.image.endpoint_type,
        'build_interval': CONF.image.build_interval,
        'build_timeout': CONF.image.build_timeout,
    }
    image_params.update(default_params)

    def __init__(self, credentials=None, service=None):
        super(Manager, self).__init__(credentials)
        for client in self.load_clients:
            getattr(self, 'set_%s' % client)()

    def set_baremetal_compute_client(self):
        self.baremetal_compute_client = BaremetalComputeClient(
            self.auth_provider, **self.baremetal_compute_params)

    def set_compute_networks_client(self):
        self.compute_networks_client = network_cli.NetworksClient(
            self.auth_provider,
            **self.compute_params)

    def set_image_client_v2(self):
        self.image_client_v2 = image_cli.ImagesClient(
            self.auth_provider,
            **self.image_params)
