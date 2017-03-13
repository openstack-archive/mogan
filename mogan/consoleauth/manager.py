# Copyright (c) 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Auth Components for Consoles."""

import time

from eventlet import greenpool
import oslo_cache
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_serialization import jsonutils

import mogan.conf
from mogan.engine import rpcapi

LOG = logging.getLogger(__name__)

CONF = mogan.conf.CONF


class ConsoleAuthManager(object):
    """Manages token based authentication."""

    target = messaging.Target(version='1.0')

    def __init__(self, host, topic):
        super(ConsoleAuthManager, self).__init__()
        self.host = host
        self.topic = topic
        self._started = False
        self._cache = None
        self._cache_instance = None
        self.engine_rpcapi = rpcapi.EngineAPI()

    def init_host(self):
        self._worker_pool = greenpool.GreenPool(
            size=CONF.engine.workers_pool_size)
        self._started = True

    def del_host(self):
        self._worker_pool.waitall()
        self._started = False

    def periodic_tasks(self, context, raise_on_error=False):
        pass

    @property
    def cache(self):
        """The recommended config example:
        [cache]
        backend_argument = url:127.0.0.1:11211
        expiration_time = 600
        backend = dogpile.cache.memcached
        enabled = True
        """
        # TODO(liusheng)may need to define config options [consoleauth]
        # section and then override to the [cache] section
        if self._cache is None:
            cache_region = oslo_cache.create_region()
            self._cache = oslo_cache.configure_cache_region(CONF, cache_region)
        return self._cache

    @property
    def cache_instance(self):
        """Init a permanent cache region for instance token storage."""
        if self._cache_instance is None:
            cache_ttl = CONF.cache.expiration_time
            try:
                CONF.set_override('expiration_time', None, 'cache')
                cache_region = oslo_cache.create_region()
                self._cache_instance = oslo_cache.configure_cache_region(
                    CONF, cache_region)
            finally:
                CONF.set_override('expiration_time', cache_ttl, 'cache')
        return self._cache_instance

    def reset(self):
        LOG.info('Reloading Mogan engine RPC API')
        self.engine_rpcapi = rpcapi.EngineAPI()

    def _get_tokens_for_instance(self, instance_uuid):
        tokens_str = self.cache_instance.get(instance_uuid.encode('UTF-8'))
        if not tokens_str:
            tokens = []
        else:
            tokens = jsonutils.loads(tokens_str)
        return tokens

    def authorize_console(self, context, token, console_type, host, port,
                          internal_access_path, instance_uuid,
                          access_url=None):

        token_dict = {'token': token,
                      'instance_uuid': instance_uuid,
                      'console_type': console_type,
                      'host': host,
                      'port': port,
                      'internal_access_path': internal_access_path,
                      'access_url': access_url,
                      'last_activity_at': time.time()}
        data = jsonutils.dumps(token_dict)

        self.cache.set(token.encode('UTF-8'), data)
        tokens = self._get_tokens_for_instance(instance_uuid)

        # Remove the expired tokens from cache.
        token_values = self.cache.get_multi(
            [tok.encode('UTF-8') for tok in tokens])
        tokens = [name for name, value in zip(tokens, token_values)
                  if value]
        tokens.append(token)

        self.cache_instance.set(instance_uuid.encode('UTF-8'),
                                jsonutils.dumps(tokens))

        LOG.info("Received Token: %(token)s, %(token_dict)s",
                 {'token': token, 'token_dict': token_dict})

    def _validate_token(self, context, token):
        instance_uuid = token['instance_uuid']
        if instance_uuid is None:
            return False
        return True
        # TODO(need to validate the console port)
        # return self.compute_rpcapi.validate_console_port(
        # context, instance, token['port'], token['console_type'])

    def check_token(self, context, token):
        token_str = self.cache.get(token.encode('UTF-8'))
        token_valid = bool(token_str)
        LOG.info("Checking Token: %(token)s, %(token_valid)s",
                 {'token': token, 'token_valid': token_valid})
        if token_valid:
            token = jsonutils.loads(token_str)
            if self._validate_token(context, token):
                return token

    def delete_tokens_for_instance(self, context, instance_uuid):
        tokens = self._get_tokens_for_instance(instance_uuid)
        self.cache.delete_multi(
            [tok.encode('UTF-8') for tok in tokens])
        self.cache_instance.delete(instance_uuid.encode('UTF-8'))
