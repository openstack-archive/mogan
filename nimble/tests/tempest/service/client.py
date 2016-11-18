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
from six.moves.urllib import parse as urllib
from tempest import config
from tempest.lib.common import rest_client
from tempest import manager

CONF = config.CONF


class BaremetalComputeClient(rest_client.RestClient):
    version = '1'
    # TODO(liusheng) since the endpoints of Nimble includes '/v1',
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


class Manager(manager.Manager):
    default_params = {
        'disable_ssl_certificate_validation':
            CONF.identity.disable_ssl_certificate_validation,
        'ca_certs': CONF.identity.ca_certificates_file,
        'trace_requests': CONF.debug.trace_requests
    }

    alarming_params = {
        'service': CONF.baremetal_compute_plugin.catalog_type,
        'region': CONF.identity.region,
        'endpoint_type': CONF.baremetal_compute_plugin.endpoint_type,
    }
    alarming_params.update(default_params)

    def __init__(self, credentials=None, service=None):
        super(Manager, self).__init__(credentials)
        self.set_baremetal_compute_client()

    def set_baremetal_compute_client(self):
        self.baremetal_compute_client = BaremetalComputeClient(
            self.auth_provider, **self.alarming_params)
