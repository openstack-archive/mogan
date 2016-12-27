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

import mock

from nimble.objects import base
from nimble.objects import fields
from nimble.tests import base as test_base
from nimble.notifications.objects import base as notification


class TestNotificationBase(test_base.BaseTestCase):
    @base.NimbleObjectRegistry.register_if(False)
    class TestObject(base.NimbleObject):
        VERSION = '1.0'
        fields = {
            'field_1': fields.StringField(),
            'field_2': fields.IntegerField(),
            'not_important_field': fields.IntegerField(),
        }

    @base.NimbleObjectRegistry.register_if(False)
    class TestNotificationPayload(notification.NotificationPayloadBase):
        VERSION = '1.0'

        SCHEMA = {
            'field_1': ('source_field', 'field_1'),
            'field_2': ('source_field', 'field_2'),
        }

        fields = {
            'extra_field': fields.StringField(),  # filled by ctor
            'field_1': fields.StringField(),  # filled by the schema
            'field_2': fields.IntegerField(),  # filled by the schema
        }

        def populate_schema(self, source_field):
            super(TestNotificationBase.TestNotificationPayload,
                  self).populate_schema(source_field=source_field)

    @base.NimbleObjectRegistry.register_if(False)
    class TestNotificationPayloadEmptySchema(
        notification.NotificationPayloadBase):
        VERSION = '1.0'

        fields = {
            'extra_field': fields.StringField(),  # filled by ctor
        }

    @notification.notification_sample('test-update-1.json')
    @notification.notification_sample('test-update-2.json')
    @base.NimbleObjectRegistry.register_if(False)
    class TestNotification(notification.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('TestNotificationPayload')
        }

    @base.NimbleObjectRegistry.register_if(False)
    class TestNotificationEmptySchema(notification.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('TestNotificationPayloadEmptySchema')
        }

    expected_payload = {
        'nimble_object.name': 'TestNotificationPayload',
        'nimble_object.data': {
            'extra_field': 'test string',
            'field_1': 'test1',
            'field_2': 42},
        'nimble_object.version': '1.0',
        'nimble_object.namespace': 'nimble'}

    def setUp(self):
        super(TestNotificationBase, self).setUp()
        self.my_obj = self.TestObject(field_1='test1',
                                      field_2=42,
                                      not_important_field=13)

        self.payload = self.TestNotificationPayload(
            extra_field='test string')
        self.payload.populate_schema(source_field=self.my_obj)

        self.notification = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE,
                phase=fields.NotificationPhase.START),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

    def _verify_notification(self, mock_notifier, mock_context,
                             expected_event_type,
                             expected_payload):
        mock_notifier.prepare.assert_called_once_with(
            publisher_id='nimble-fake:fake-host')
        mock_notify = mock_notifier.prepare.return_value.info
        self.assertTrue(mock_notify.called)
        self.assertEqual(mock_notify.call_args[0][0], mock_context)
        self.assertEqual(mock_notify.call_args[1]['event_type'],
                         expected_event_type)
        actual_payload = mock_notify.call_args[1]['payload']
        self.assertJsonEqual(expected_payload, actual_payload)

    @mock.patch('nimble.common.rpc.NOTIFIER')
    def test_emit_notification(self, mock_notifier, mock_legacy):
        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        self.notification.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update.start',
            expected_payload=self.expected_payload)
        self.assertFalse(mock_legacy.called)

    @mock.patch('nimble.common.rpc.NOTIFIER')
    def test_emit_with_host_and_binary_as_publisher(self, mock_notifier):
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher(host='fake-host',
                                                         binary='nimble-fake'),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)

    @mock.patch('nimble.common.rpc.NOTIFIER')
    def test_emit_event_type_without_phase(self, mock_notifier, mock_legacy):
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)
        self.assertFalse(mock_legacy.called)

    @mock.patch('nimble.common.rpc.NOTIFIER')
    def test_not_possible_to_emit_if_not_populated(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayload(
            extra_field='test string')
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        self.assertRaises(AssertionError, noti.emit, mock_context)
        self.assertFalse(mock_notifier.called)

    @mock.patch('nimble.common.rpc.NOTIFIER')
    def test_empty_schema(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayloadEmptySchema(
            extra_field='test string')
        noti = self.TestNotificationEmptySchema(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=
            {'nimble_object.name': 'TestNotificationPayloadEmptySchema',
             'nimble_object.data': {'extra_field': u'test string'},
             'nimble_object.version': '1.0',
             'nimble_object.namespace': 'nimble'})

    def test_sample_decorator(self):
        self.assertEqual(2, len(self.TestNotification.samples))
        self.assertIn('test-update-1.json', self.TestNotification.samples)
        self.assertIn('test-update-2.json', self.TestNotification.samples)
