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
import collections

import mock
from oslo_versionedobjects import fixture as object_fixture

from mogan.notifications import base as notification_base
from mogan.notifications.objects import base as notification
from mogan.objects import base
from mogan.objects import fields
from mogan.objects import server as server_obj
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
        mock_notifier.assert_not_called()

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


notification_object_data = {
    'ServerPayload': '1.0-6a060a6bebc672c105c14b4cef979527',
    'ServerActionPayload': '1.0-b558fd2bcce6388507b67a834f09689f',
    'ServerActionNotification': '1.0-20087e599436bd9db62ae1fb5e2dfef2',
    'ExceptionPayload': '1.0-7c31986d8d78bed910c324965c431e18',
    'ExceptionNotification': '1.0-20087e599436bd9db62ae1fb5e2dfef2',
    'EventType': '1.0-93493dd78bdfed806fca70c91d85cbb4',
    'NotificationPublisher': '1.0-4b0b0d662b21eeed0b23617f3f11794b'
}


class TestNotificationObjectVersions(test_base.TestCase):
    def setUp(self):
        super(test_base.TestCase, self).setUp()
        base.MoganObjectRegistry.register_notification_objects()

    def test_versions(self):
        noti_class = base.MoganObjectRegistry.notification_classes
        classes = {cls.__name__: [cls] for cls in noti_class}
        checker = object_fixture.ObjectVersionChecker(obj_classes=classes)
        # Compute the difference between actual fingerprints and
        # expect fingerprints. expect = actual = {} if there is no change.
        expect, actual = checker.test_hashes(notification_object_data)
        self.assertEqual(expect, actual,
                         "Some objects fields or remotable methods have been "
                         "modified. Please make sure the version of those "
                         "objects have been bumped and then update "
                         "expected_object_fingerprints with the new hashes. ")

    def test_notification_payload_version_depends_on_the_schema(self):
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
                'field_2': fields.IntegerField(),   # filled by the schema
            }

        checker = object_fixture.ObjectVersionChecker(
            {'TestNotificationPayload': (TestNotificationPayload,)})

        old_hash = checker.get_hashes(extra_data_func=get_extra_data)
        TestNotificationPayload.SCHEMA['field_3'] = ('source_field',
                                                     'field_3')
        new_hash = checker.get_hashes(extra_data_func=get_extra_data)

        self.assertNotEqual(old_hash, new_hash)


def get_extra_data(obj_class):
    extra_data = tuple()

    # Get the SCHEMA items to add to the fingerprint
    # if we are looking at a notification
    if issubclass(obj_class, notification.NotificationPayloadBase):
        schema_data = collections.OrderedDict(
            sorted(obj_class.SCHEMA.items()))

        extra_data += (schema_data,)

    return extra_data


class TestServerActionNotification(test_base.TestCase):
    @mock.patch('mogan.notifications.objects.server.'
                'ServerActionNotification._emit')
    def test_send_version_server_action(self, mock_emit):
        # Make sure that the notification payload chooses the values in
        # server.flavor.$value instead of server.$value
        fake_server_values = db_utils.get_test_server()
        server = server_obj.Server(**fake_server_values)
        notification_base.notify_about_server_action(
            mock.MagicMock(),
            server,
            'test-host',
            fields.NotificationAction.CREATE,
            fields.NotificationPhase.START,
            'mogan-compute')
        self.assertEqual('server.create.start',
                         mock_emit.call_args_list[0][1]['event_type'])
        self.assertEqual('mogan-compute:test-host',
                         mock_emit.call_args_list[0][1]['publisher_id'])
        payload = mock_emit.call_args_list[0][1]['payload'][
            'mogan_object.data']
        self.assertEqual(fake_server_values['uuid'], payload['uuid'])
        self.assertEqual(fake_server_values['flavor_uuid'],
                         payload['flavor_uuid'])
        self.assertEqual(fake_server_values['status'], payload['status'])
        self.assertEqual(fake_server_values['user_id'], payload['user_id'])
        self.assertEqual(fake_server_values['availability_zone'],
                         payload['availability_zone'])
        self.assertEqual(fake_server_values['name'], payload['name'])
        self.assertEqual(fake_server_values['image_uuid'],
                         payload['image_uuid'])
        self.assertEqual(fake_server_values['project_id'],
                         payload['project_id'])
        self.assertEqual(fake_server_values['description'],
                         payload['description'])
        self.assertEqual(fake_server_values['power_state'],
                         payload['power_state'])
