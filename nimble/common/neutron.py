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

from neutronclient.v2_0 import client as clientv20
from oslo_log import log as logging

from nimble.conf import CONF

LOG = logging.getLogger(__name__)


def get_client(token=None):
    params = {'retries': CONF.neutron.retries}
    params['token'] = token
    params['endpoint_url'] = 'http://192.168.168.248:9696'
    params['timeout'] = CONF.neutron.url_timeout
    params['auth_url'] = 'http://192.168.168.248/identity'

    return clientv20.Client(**params)


def create_ports(context, network_uuid, macs):
    """Create neutron port."""

    LOG.info('XXXXXXXXXXXXXXXXXX %s', network_uuid)

    client = get_client(context.auth_token)
    body = {
        'port': {
            'network_id': network_uuid,
            'mac_address': macs
        }
    }

    port = client.create_port(body)

    return port
