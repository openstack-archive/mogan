# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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
Tests For Scheduler
"""

import mock
from oslo_config import cfg

from nimble.common import context
from nimble import db
from nimble.common import exception
#from cinder.message import defined_messages
from nimble import objects
from nimble.objects import fields
from nimble.engine.scheduler import driver
from nimble.engine.scheduler import filter_scheduler
from nimble.engine.scheduler import manager
from nimble.tests import base as test

from cinder.tests.unit import fake_constants as fake
from cinder.tests.unit import fake_volume
from cinder.tests.unit import utils as tests_utils

CONF = cfg.CONF


class SchedulerManagerTestCase(test.TestCase):
    """Test case for scheduler manager."""

    manager_cls = manager.SchedulerManager
    driver_cls = driver.Scheduler
    driver_cls_name = 'cinder.scheduler.driver.Scheduler'

    class AnException(Exception):
        pass

    def setUp(self):
        super(SchedulerManagerTestCase, self).setUp()
        self.flags(scheduler_driver=self.driver_cls_name)
        self.manager = self.manager_cls()
        self.manager._startup_delay = False
        self.context = context.get_admin_context()
        self.topic = 'fake_topic'
        self.fake_args = (1, 2, 3)
        self.fake_kwargs = {'cat': 'meow', 'dog': 'woof'}

    def test_1_correct_init(self):
        # Correct scheduler driver
        manager = self.manager
        self.assertIsInstance(manager.driver, self.driver_cls)

    @mock.patch('eventlet.sleep')
    @mock.patch('cinder.volume.rpcapi.VolumeAPI.publish_service_capabilities')
    def test_init_host_with_rpc(self, publish_capabilities_mock, sleep_mock):
        self.manager._startup_delay = True
        self.manager.init_host_with_rpc()
        publish_capabilities_mock.assert_called_once_with(mock.ANY)
        sleep_mock.assert_called_once_with(CONF.periodic_interval)
        self.assertFalse(self.manager._startup_delay)

    @mock.patch('cinder.objects.service.Service.get_minimum_rpc_version')
    @mock.patch('cinder.objects.service.Service.get_minimum_obj_version')
    @mock.patch('cinder.rpc.LAST_RPC_VERSIONS', {'cinder-volume': '1.3'})
    @mock.patch('cinder.rpc.LAST_OBJ_VERSIONS', {'cinder-volume': '1.4'})
    def test_reset(self, get_min_obj, get_min_rpc):
        mgr = self.manager_cls()

        volume_rpcapi = mgr.driver.volume_rpcapi
        self.assertEqual('1.3', volume_rpcapi.client.version_cap)
        self.assertEqual('1.4',
                         volume_rpcapi.client.serializer._base.version_cap)
        get_min_obj.return_value = objects.base.OBJ_VERSIONS.get_current()
        mgr.reset()

        volume_rpcapi = mgr.driver.volume_rpcapi
        self.assertEqual(get_min_rpc.return_value,
                         volume_rpcapi.client.version_cap)
        self.assertEqual(get_min_obj.return_value,
                         volume_rpcapi.client.serializer._base.version_cap)
        self.assertIsNone(volume_rpcapi.client.serializer._base.manifest)

    @mock.patch('cinder.scheduler.driver.Scheduler.'
                'update_service_capabilities')
    def test_update_service_capabilities_empty_dict(self, _mock_update_cap):
        # Test no capabilities passes empty dictionary
        service = 'fake_service'
        host = 'fake_host'

        self.manager.update_service_capabilities(self.context,
                                                 service_name=service,
                                                 host=host)
        _mock_update_cap.assert_called_once_with(service, host, {})

    @mock.patch('cinder.scheduler.driver.Scheduler.'
                'update_service_capabilities')
    def test_update_service_capabilities_correct(self, _mock_update_cap):
        # Test capabilities passes correctly
        service = 'fake_service'
        host = 'fake_host'
        capabilities = {'fake_capability': 'fake_value'}

        self.manager.update_service_capabilities(self.context,
                                                 service_name=service,
                                                 host=host,
                                                 capabilities=capabilities)
        _mock_update_cap.assert_called_once_with(service, host, capabilities)

    @mock.patch('cinder.scheduler.driver.Scheduler.schedule_create_volume')
    @mock.patch('cinder.message.api.API.create')
    @mock.patch('cinder.db.volume_update')
    def test_create_volume_exception_puts_volume_in_error_state(
            self, _mock_volume_update, _mock_message_create,
            _mock_sched_create):
        # Test NoValidHost exception behavior for create_volume.
        # Puts the volume in 'error' state and eats the exception.
        _mock_sched_create.side_effect = exception.NoValidHost(reason="")
        volume = fake_volume.fake_volume_obj(self.context)
        topic = 'fake_topic'
        request_spec = {'volume_id': volume.id,
                        'volume': {'id': volume.id, '_name_id': None,
                                   'metadata': {}, 'admin_metadata': {},
                                   'glance_metadata': {}}}
        request_spec_obj = objects.RequestSpec.from_primitives(request_spec)

        self.manager.create_volume(self.context, topic, volume.id,
                                   request_spec=request_spec,
                                   filter_properties={},
                                   volume=volume)
        _mock_volume_update.assert_called_once_with(self.context,
                                                    volume.id,
                                                    {'status': 'error'})
        _mock_sched_create.assert_called_once_with(self.context,
                                                   request_spec_obj, {})

        _mock_message_create.assert_called_once_with(
            self.context, defined_messages.UNABLE_TO_ALLOCATE,
            self.context.project_id, resource_type='VOLUME',
            resource_uuid=volume.id)

    @mock.patch('cinder.scheduler.driver.Scheduler.schedule_create_volume')
    @mock.patch('eventlet.sleep')
    def test_create_volume_no_delay(self, _mock_sleep, _mock_sched_create):
        volume = fake_volume.fake_volume_obj(self.context)
        topic = 'fake_topic'

        request_spec = {'volume_id': volume.id}
        request_spec_obj = objects.RequestSpec.from_primitives(request_spec)

        self.manager.create_volume(self.context, topic, volume.id,
                                   request_spec=request_spec,
                                   filter_properties={},
                                   volume=volume)
        _mock_sched_create.assert_called_once_with(self.context,
                                                   request_spec_obj, {})
        self.assertFalse(_mock_sleep.called)

    @mock.patch('cinder.scheduler.driver.Scheduler.schedule_create_volume')
    @mock.patch('cinder.scheduler.driver.Scheduler.is_ready')
    @mock.patch('eventlet.sleep')
    def test_create_volume_delay_scheduled_after_3_tries(self, _mock_sleep,
                                                         _mock_is_ready,
                                                         _mock_sched_create):
        self.manager._startup_delay = True
        volume = fake_volume.fake_volume_obj(self.context)
        topic = 'fake_topic'

        request_spec = {'volume_id': volume.id}
        request_spec_obj = objects.RequestSpec.from_primitives(request_spec)

        _mock_is_ready.side_effect = [False, False, True]

        self.manager.create_volume(self.context, topic, volume.id,
                                   request_spec=request_spec,
                                   filter_properties={},
                                   volume=volume)
        _mock_sched_create.assert_called_once_with(self.context,
                                                   request_spec_obj, {})
        calls = [mock.call(1)] * 2
        _mock_sleep.assert_has_calls(calls)
        self.assertEqual(2, _mock_sleep.call_count)

    @mock.patch('cinder.scheduler.driver.Scheduler.schedule_create_volume')
    @mock.patch('cinder.scheduler.driver.Scheduler.is_ready')
    @mock.patch('eventlet.sleep')
    def test_create_volume_delay_scheduled_in_1_try(self, _mock_sleep,
                                                    _mock_is_ready,
                                                    _mock_sched_create):
        self.manager._startup_delay = True
        volume = fake_volume.fake_volume_obj(self.context)
        topic = 'fake_topic'

        request_spec = {'volume_id': volume.id}
        request_spec_obj = objects.RequestSpec.from_primitives(request_spec)

        _mock_is_ready.return_value = True

        self.manager.create_volume(self.context, topic, volume.id,
                                   request_spec=request_spec,
                                   filter_properties={},
                                   volume=volume)
        _mock_sched_create.assert_called_once_with(self.context,
                                                   request_spec_obj, {})
        self.assertFalse(_mock_sleep.called)

    @mock.patch('cinder.db.volume_get')
    @mock.patch('cinder.scheduler.driver.Scheduler.host_passes_filters')
    @mock.patch('cinder.db.volume_update')
    def test_migrate_volume_exception_returns_volume_state(
            self, _mock_volume_update, _mock_host_passes,
            _mock_volume_get):
        # Test NoValidHost exception behavior for migrate_volume_to_host.
        # Puts the volume in 'error_migrating' state and eats the exception.
        fake_updates = {'migration_status': 'error'}
        self._test_migrate_volume_exception_returns_volume_state(
            _mock_volume_update, _mock_host_passes, _mock_volume_get,
            'available', fake_updates)

    @mock.patch('cinder.db.volume_get')
    @mock.patch('cinder.scheduler.driver.Scheduler.host_passes_filters')
    @mock.patch('cinder.db.volume_update')
    def test_migrate_volume_exception_returns_volume_state_maintenance(
            self, _mock_volume_update, _mock_host_passes,
            _mock_volume_get):
        fake_updates = {'status': 'available',
                        'migration_status': 'error'}
        self._test_migrate_volume_exception_returns_volume_state(
            _mock_volume_update, _mock_host_passes, _mock_volume_get,
            'maintenance', fake_updates)

    def _test_migrate_volume_exception_returns_volume_state(
            self, _mock_volume_update, _mock_host_passes,
            _mock_volume_get, status, fake_updates):
        volume = tests_utils.create_volume(self.context,
                                           status=status,
                                           previous_status='available')
        fake_volume_id = volume.id
        topic = 'fake_topic'
        request_spec = {'volume_id': fake_volume_id}
        _mock_host_passes.side_effect = exception.NoValidHost(reason="")
        _mock_volume_get.return_value = volume

        self.manager.migrate_volume_to_host(self.context, topic,
                                            fake_volume_id, 'host', True,
                                            request_spec=request_spec,
                                            filter_properties={},
                                            volume=volume)
        _mock_volume_update.assert_called_once_with(self.context,
                                                    fake_volume_id,
                                                    fake_updates)
        _mock_host_passes.assert_called_once_with(self.context, 'host',
                                                  request_spec, {})

    @mock.patch('cinder.db.volume_update')
    @mock.patch('cinder.db.volume_attachment_get_all_by_volume_id')
    @mock.patch('cinder.quota.QUOTAS.rollback')
    def test_retype_volume_exception_returns_volume_state(
            self, quota_rollback, _mock_vol_attachment_get, _mock_vol_update):
        # Test NoValidHost exception behavior for retype.
        # Puts the volume in original state and eats the exception.
        volume = tests_utils.create_volume(self.context,
                                           status='retyping',
                                           previous_status='in-use')
        instance_uuid = '12345678-1234-5678-1234-567812345678'
        volume_attach = tests_utils.attach_volume(self.context, volume.id,
                                                  instance_uuid, None,
                                                  '/dev/fake')
        _mock_vol_attachment_get.return_value = [volume_attach]
        topic = 'fake_topic'
        reservations = mock.sentinel.reservations
        request_spec = {'volume_id': volume.id, 'volume_type': {'id': 3},
                        'migration_policy': 'on-demand',
                        'quota_reservations': reservations}
        _mock_vol_update.return_value = {'status': 'in-use'}
        _mock_find_retype_host = mock.Mock(
            side_effect=exception.NoValidHost(reason=""))
        orig_retype = self.manager.driver.find_retype_host
        self.manager.driver.find_retype_host = _mock_find_retype_host

        self.manager.retype(self.context, topic, volume.id,
                            request_spec=request_spec,
                            filter_properties={},
                            volume=volume)

        _mock_find_retype_host.assert_called_once_with(self.context,
                                                       request_spec, {},
                                                       'on-demand')
        quota_rollback.assert_called_once_with(self.context, reservations)
        _mock_vol_update.assert_called_once_with(self.context, volume.id,
                                                 {'status': 'in-use'})
        self.manager.driver.find_retype_host = orig_retype

    def test_create_consistencygroup_exceptions(self):
        with mock.patch.object(filter_scheduler.FilterScheduler,
                               'schedule_create_consistencygroup') as mock_cg:
            original_driver = self.manager.driver
            consistencygroup_obj = \
                fake_consistencygroup.fake_consistencyobject_obj(self.context)
            self.manager.driver = filter_scheduler.FilterScheduler
            LOG = self.mock_object(manager, 'LOG')
            self.mock_object(db, 'consistencygroup_update')

            ex = exception.CinderException('test')
            mock_cg.side_effect = ex
            group_id = fake.CONSISTENCY_GROUP_ID
            self.assertRaises(exception.CinderException,
                              self.manager.create_consistencygroup,
                              self.context,
                              'volume',
                              consistencygroup_obj)
            self.assertGreater(LOG.exception.call_count, 0)
            db.consistencygroup_update.assert_called_once_with(
                self.context, group_id, {'status': (
                    fields.ConsistencyGroupStatus.ERROR)})

            mock_cg.reset_mock()
            LOG.exception.reset_mock()
            db.consistencygroup_update.reset_mock()

            mock_cg.side_effect = exception.NoValidHost(
                reason="No weighed hosts available")
            self.manager.create_consistencygroup(
                self.context, 'volume', consistencygroup_obj)
            self.assertGreater(LOG.error.call_count, 0)
            db.consistencygroup_update.assert_called_once_with(
                self.context, group_id, {'status': (
                    fields.ConsistencyGroupStatus.ERROR)})

            self.manager.driver = original_driver


class SchedulerTestCase(test.TestCase):
    """Test case for base scheduler driver class."""

    # So we can subclass this test and re-use tests if we need.
    driver_cls = driver.Scheduler

    def setUp(self):
        super(SchedulerTestCase, self).setUp()
        self.driver = self.driver_cls()
        self.context = context.RequestContext(fake.USER_ID, fake.PROJECT_ID)
        self.topic = 'fake_topic'

    @mock.patch('cinder.scheduler.driver.Scheduler.'
                'update_service_capabilities')
    def test_update_service_capabilities(self, _mock_update_cap):
        service_name = 'fake_service'
        host = 'fake_host'
        capabilities = {'fake_capability': 'fake_value'}
        self.driver.update_service_capabilities(service_name, host,
                                                capabilities)
        _mock_update_cap.assert_called_once_with(service_name, host,
                                                 capabilities)

    @mock.patch('cinder.scheduler.host_manager.HostManager.'
                'has_all_capabilities', return_value=False)
    def test_is_ready(self, _mock_has_caps):
        ready = self.driver.is_ready()
        _mock_has_caps.assert_called_once_with()
        self.assertFalse(ready)


class SchedulerDriverBaseTestCase(SchedulerTestCase):
    """Test schedule driver class.

    Test cases for base scheduler driver class methods
    that will fail if the driver is changed.
    """

    def test_unimplemented_schedule(self):
        fake_args = (1, 2, 3)
        fake_kwargs = {'cat': 'meow'}

        self.assertRaises(NotImplementedError, self.driver.schedule,
                          self.context, self.topic, 'schedule_something',
                          *fake_args, **fake_kwargs)


class SchedulerDriverModuleTestCase(test.TestCase):
    """Test case for scheduler driver module methods."""

    def setUp(self):
        super(SchedulerDriverModuleTestCase, self).setUp()
        self.context = context.RequestContext(fake.USER_ID, fake.PROJECT_ID)

    @mock.patch('cinder.db.volume_update')
    @mock.patch('cinder.objects.volume.Volume.get_by_id')
    def test_volume_host_update_db(self, _mock_volume_get, _mock_vol_update):
        volume = fake_volume.fake_volume_obj(self.context)
        _mock_volume_get.return_value = volume

        driver.volume_update_db(self.context, volume.id, 'fake_host')
        scheduled_at = volume.scheduled_at.replace(tzinfo=None)
        _mock_vol_update.assert_called_once_with(
            self.context, volume.id, {'host': 'fake_host',
                                      'scheduled_at': scheduled_at})
