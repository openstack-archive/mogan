# Copyright 2017 Huawei Technologies Co.,LTD.
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
"""
Tests For ConsoleAuth manager
"""
import time

import mock

from mogan.consoleauth import manager
from mogan.tests import base as test


class ConsoleAuthManagerTestCase(test.TestCase):
    """Test case for ConsoleAuthManager class."""

    def setUp(self):
        super(ConsoleAuthManagerTestCase, self).setUp()
        self.manager = manager.ConsoleAuthManager('test-host',
                                                  'test-consoleauth-topic')
        self.server_uuid = 'e7481762-3215-4489-bde5-0068a6bf79d1'
        self.config(backend='oslo_cache.dict', enabled=True,
                    group='cache')
        self.addCleanup(
            self.manager.delete_tokens_for_server, self.context,
            self.server_uuid)

    def test_reset(self):
        with mock.patch('mogan.engine.rpcapi.EngineAPI') as mock_rpc:
            old_rpcapi = self.manager.engine_rpcapi
            self.manager.reset()
            mock_rpc.assert_called_once_with()
            self.assertNotEqual(old_rpcapi,
                                self.manager.engine_rpcapi)

    def test_tokens_expire(self):
        # Test that tokens expire correctly.
        token = u'mytok'
        self.config(expiration_time=1, group='cache')
        self.manager.authorize_console(
            self.context, token, 'shellinabox', '127.0.0.1', 4321,
            None, self.server_uuid, None)
        self.assertIsNotNone(self.manager.check_token(self.context, token))
        time.sleep(1)
        self.assertIsNone(self.manager.check_token(self.context, token))

    def test_multiple_tokens_for_server(self):
        tokens = [u"token" + str(i) for i in range(10)]

        for token in tokens:
            self.manager.authorize_console(
                self.context, token, 'shellinabox', '127.0.0.1', 4321,
                None, self.server_uuid, None)

        for token in tokens:
            self.assertIsNotNone(
                self.manager.check_token(self.context, token))

    def test_delete_tokens_for_server(self):
        tokens = [u"token" + str(i) for i in range(10)]
        for token in tokens:
            self.manager.authorize_console(
                self.context, token, 'shellinabox', '127.0.0.1', 4321,
                None, self.server_uuid, None)
        self.manager.delete_tokens_for_server(self.context,
                                              self.server_uuid)
        stored_tokens = self.manager._get_tokens_for_server(
            self.server_uuid)

        self.assertEqual(len(stored_tokens), 0)

        for token in tokens:
            self.assertIsNone(
                self.manager.check_token(self.context, token))

    def test_delete_expired_tokens(self):
        token = u'mytok'
        self.config(expiration_time=1, group='cache')

        self.manager.authorize_console(
            self.context, token, 'shellinabox', '127.0.0.1', 4321,
            None, self.server_uuid, None)
        time.sleep(1)
        self.assertIsNone(self.manager.check_token(self.context, token))

        token1 = u'mytok2'
        self.manager.authorize_console(
            self.context, token1, 'shellinabox', '127.0.0.1', 4321,
            None, self.server_uuid, None)
        stored_tokens = self.manager._get_tokens_for_server(
            self.server_uuid)
        # when trying to store token1, expired token is removed fist.
        self.assertEqual(len(stored_tokens), 1)
        self.assertEqual(stored_tokens[0], token1)
