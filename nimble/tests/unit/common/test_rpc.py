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

import mock

from oslo_config import cfg
from oslo_context import context as nimble_context
import oslo_messaging as messaging

from nimble.common import rpc
from nimble.tests import base

CONF = cfg.CONF


class TestUtils(base.TestCase):

    @mock.patch.object(messaging, 'Notifier', autospec=True)
    @mock.patch.object(messaging, 'JsonPayloadSerializer', autospec=True)
    @mock.patch.object(messaging, 'get_notification_transport', autospec=True)
    @mock.patch.object(messaging, 'get_transport', autospec=True)
    def test_init_globals_notifications(self, mock_get_transport,
                                        mock_get_notification,
                                        mock_json_serializer,
                                        mock_notifier):
        self._test_init_globals(mock_get_transport, mock_get_notification,
                                mock_json_serializer, mock_notifier)

    def _test_init_globals(self, mock_get_transport, mock_get_notification,
                           mock_json_serializer, mock_notifier):
        rpc.TRANSPORT = None
        rpc.NOTIFICATION_TRANSPORT = None
        mock_request_serializer = mock.Mock()
        mock_request_serializer.return_value = mock.Mock()
        rpc.RequestContextSerializer = mock_request_serializer

        # Make sure that two separate Notifiers are instantiated: one for the
        # regular RPC transport, one for the notification transport
        mock_notifiers = [mock.Mock()] * 2
        mock_notifier.side_effect = mock_notifiers

        rpc.init(CONF)

        self.assertEqual(mock_get_transport.return_value, rpc.TRANSPORT)
        self.assertEqual(mock_get_notification.return_value,
                         rpc.NOTIFICATION_TRANSPORT)
        self.assertTrue(mock_json_serializer.called)

        notifier_calls = [
            mock.call(
                rpc.NOTIFICATION_TRANSPORT,
                serializer=mock_request_serializer.return_value),
        ]

        mock_notifier.assert_has_calls(notifier_calls)


class TestRequestContextSerializer(base.TestCase):

    def setUp(self):
        super(TestRequestContextSerializer, self).setUp()

        self.mock_serializer = mock.MagicMock()
        self.serializer = rpc.RequestContextSerializer(self.mock_serializer)
        self.context = nimble_context.RequestContext()
        self.entity = {'foo': 'bar'}

    def test_serialize_entity(self):
        self.serializer.serialize_entity(self.context, self.entity)
        self.mock_serializer.serialize_entity.assert_called_with(
            self.context, self.entity)

    def test_serialize_entity_empty_base(self):
        # NOTE(viktors): Return False for check `if self.serializer._base:`
        bool_args = {'__bool__': lambda *args: False,
                     '__nonzero__': lambda *args: False}
        self.mock_serializer.configure_mock(**bool_args)

        entity = self.serializer.serialize_entity(self.context, self.entity)
        self.assertFalse(self.mock_serializer.serialize_entity.called)
        # If self.serializer._base is empty, return entity directly
        self.assertEqual(self.entity, entity)

    def test_deserialize_entity(self):
        self.serializer.deserialize_entity(self.context, self.entity)
        self.mock_serializer.deserialize_entity.assert_called_with(
            self.context, self.entity)

    def test_deserialize_entity_empty_base(self):
        # NOTE(viktors): Return False for check `if self.serializer._base:`
        bool_args = {'__bool__': lambda *args: False,
                     '__nonzero__': lambda *args: False}
        self.mock_serializer.configure_mock(**bool_args)

        entity = self.serializer.deserialize_entity(self.context, self.entity)
        self.assertFalse(self.mock_serializer.serialize_entity.called)
        self.assertEqual(self.entity, entity)

    def test_serialize_context(self):
        serialize_values = self.serializer.serialize_context(self.context)

        self.assertEqual(self.context.to_dict(), serialize_values)

    def test_deserialize_context(self):
        self.context.user = 'fake-user'
        self.context.tenant = 'fake-tenant'
        serialize_values = self.context.to_dict()
        new_context = self.serializer.deserialize_context(serialize_values)
        # Nimble RequestContext from_dict will pop 'user' and 'tenant' and
        # initialize to None.
        self.assertIsNone(new_context.user)
        self.assertIsNone(new_context.tenant)
