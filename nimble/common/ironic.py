# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ironicclient import client
from oslo_config import cfg

from nimble.common import keystone

CONF = cfg.CONF

# 1.11 is API version, which support 'enroll' state
DEFAULT_IRONIC_API_VERSION = '1.11'

IRONIC_GROUP = 'ironic'

IRONIC_SESSION = None
LEGACY_MAP = {
    'auth_url': 'os_auth_url',
    'username': 'os_username',
    'password': 'os_password',
    'tenant_name': 'os_tenant_name'
}


def get_client(token=None,
               api_version=DEFAULT_IRONIC_API_VERSION):  # pragma: no cover
    """Get Ironic client instance."""
    # NOTE: To support standalone ironic without keystone
    if CONF.ironic.auth_strategy == 'noauth':
        args = {'token': 'noauth',
                'endpoint': CONF.ironic.ironic_url}
    else:
        global IRONIC_SESSION
        if not IRONIC_SESSION:
            IRONIC_SESSION = keystone.get_session(
                IRONIC_GROUP, legacy_mapping=LEGACY_MAP)
        if token is None:
            args = {'session': IRONIC_SESSION,
                    'region_name': CONF.ironic.os_region}
        else:
            ironic_url = IRONIC_SESSION.get_endpoint(
                service_type=CONF.ironic.os_service_type,
                endpoint_type=CONF.ironic.os_endpoint_type,
                region_name=CONF.ironic.os_region
            )
            args = {'token': token,
                    'endpoint': ironic_url}
    args['os_ironic_api_version'] = api_version
    args['max_retries'] = CONF.ironic.max_retries
    args['retry_interval'] = CONF.ironic.retry_interval
    return client.Client(1, **args)
