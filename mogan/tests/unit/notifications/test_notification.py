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

from mogan.notifications import base as notification_base
from mogan.notifications.objects import base as notification
from mogan.objects import base
from mogan.objects import fields
from mogan.objects import instance as inst_obj
from mogan.tests import base as test_base
from mogan.tests.unit.db import utils as db_utils


class TestNotificationBase(test_base.TestCase):
    @base.MoganObjectRegistry.register_if(False)
    class TestObject(base.MoganObject):
        VERSION = '1.0'
        fields = {
            'field_1': fields.StringField(),
            'field_2': fields.IntegerField(),
            'not_important_field': fields.IntegerField(),
        }

    @base.MoganObjectRegistry.register_if(False)
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

    @base.MoganObjectRegistry.register_if(False)
    class TestNotificationPayloadEmptySchema(
            notification.NotificationPayloadBase):
        VERSION = '1.0'

        fields = {
            'extra_field': fields.StringField(),  # filled by ctor
        }

    @notification.notification_sample('test-update-1.json')
    @notification.notification_sample('test-update-2.json')
    @base.MoganObjectRegistry.register_if(False)
    class TestNotification(notification.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('TestNotificationPayload')
        }

    @base.MoganObjectRegistry.register_if(False)
    class TestNotificationEmptySchema(notification.NotificationBase):
        VERSION = '1.0'
        fields = {
            'payload': fields.ObjectField('TestNotificationPayloadEmptySchema')
        }

    expected_payload = {
        'mogan_object.name': 'TestNotificationPayload',
        'mogan_object.data': {
            'extra_field': 'test string',
            'field_1': 'test1',
            'field_2': 42},
        'mogan_object.version': '1.0',
        'mogan_object.namespace': 'mogan'}

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
            publisher=notification.NotificationPublisher(
                host='fake-host', binary='mogan-fake'),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

    def _verify_notification(self, mock_notifier, mock_context,
                             expected_event_type,
                             expected_payload):
        mock_notifier.prepare.assert_called_once_with(
            publisher_id='mogan-fake:fake-host')
        mock_notify = mock_notifier.prepare.return_value.info
        self.assertTrue(mock_notify.called)
        self.assertEqual(mock_notify.call_args[0][0], mock_context)
        self.assertEqual(mock_notify.call_args[1]['event_type'],
                         expected_event_type)
        actual_payload = mock_notify.call_args[1]['payload']
        self.assertJsonEqual(expected_payload, actual_payload)

    @mock.patch('mogan.common.rpc.NOTIFIER')
    def test_emit_notification(self, mock_notifier):
        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        self.notification.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update.start',
            expected_payload=self.expected_payload)

    @mock.patch('mogan.common.rpc.NOTIFIER')
    def test_emit_with_host_and_binary_as_publisher(self, mock_notifier):
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher(
                host='fake-host', binary='mogan-fake'),
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

    @mock.patch('mogan.common.rpc.NOTIFIER')
    def test_emit_event_type_without_phase(self, mock_notifier):
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher(
                host='fake-host', binary='mogan-fake'),
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

    @mock.patch('mogan.common.rpc.NOTIFIER')
    def test_not_possible_to_emit_if_not_populated(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayload(
            extra_field='test string')
        noti = self.TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher(
                host='fake-host', binary='mogan-fake'),
            priority=fields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        self.assertRaises(AssertionError, noti.emit, mock_context)
        self.assertFalse(mock_notifier.called)

    @mock.patch('mogan.common.rpc.NOTIFIER')
    def test_empty_schema(self, mock_notifier):
        non_populated_payload = self.TestNotificationPayloadEmptySchema(
            extra_field='test string')
        noti = self.TestNotificationEmptySchema(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher(
                host='fake-host', binary='mogan-fake'),
            priority=fields.NotificationPriority.INFO,
            payload=non_populated_payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload={
                'mogan_object.name': 'TestNotificationPayloadEmptySchema',
                'mogan_object.data': {'extra_field': u'test string'},
                'mogan_object.version': '1.0',
                'mogan_object.namespace': 'mogan'})

    def test_sample_decorator(self):
        self.assertEqual(2, len(self.TestNotification.samples))
        self.assertIn('test-update-1.json', self.TestNotification.samples)
        self.assertIn('test-update-2.json', self.TestNotification.samples)


class TestInstanceActionNotification(test_base.TestCase):
    @mock.patch('mogan.notifications.objects.instance.'
                'InstanceActionNotification._emit')
    def test_send_version_instance_action(self, mock_emit):
        # Make sure that the notification payload chooses the values in
        # instance.flavor.$value instead of instance.$value
        fake_inst_values = db_utils.get_test_instance()
        instance = inst_obj.Instance(**fake_inst_values)
        notification_base.notify_about_instance_action(
            mock.MagicMock(),
            instance,
            'test-host',
            fields.NotificationAction.CREATE,
            fields.NotificationPhase.START,
            'mogan-compute')
        self.assertEqual('instance.create.start',
                         mock_emit.call_args_list[0][1]['event_type'])
        self.assertEqual('mogan-compute:test-host',
                         mock_emit.call_args_list[0][1]['publisher_id'])
        payload = mock_emit.call_args_list[0][1]['payload'][
            'mogan_object.data']
        self.assertEqual(fake_inst_values['uuid'], payload['uuid'])
        self.assertEqual(fake_inst_values['instance_type_uuid'],
                         payload['instance_type_uuid'])
        self.assertEqual(fake_inst_values['status'], payload['status'])
        self.assertEqual(fake_inst_values['user_id'], payload['user_id'])
        self.assertEqual(fake_inst_values['availability_zone'],
                         payload['availability_zone'])
        self.assertEqual(fake_inst_values['name'], payload['name'])
        self.assertEqual(fake_inst_values['image_uuid'], payload['image_uuid'])
        self.assertEqual(fake_inst_values['project_id'], payload['project_id'])
        self.assertEqual(fake_inst_values['description'],
                         payload['description'])
