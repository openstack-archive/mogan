# Copyright 2016 Huawei Technologies Co.,LTD.
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

"""Unit tests for engine API."""

import mock
from oslo_context import context

from mogan.common import exception
from mogan.common import states
from mogan.engine import api as engine_api
from mogan.engine import rpcapi as engine_rpcapi
from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils as db_utils


class ComputeAPIUnitTest(base.DbTestCase):
    def setUp(self):
        super(ComputeAPIUnitTest, self).setUp()
        self.user_id = 'fake-user'
        self.project_id = 'fake-project'
        self.engine_api = engine_api.API()
        self.context = context.RequestContext(user=self.user_id,
                                              tenant=self.project_id)

    def _create_instance_type(self):
        inst_type = db_utils.get_test_instance_type()
        inst_type['extra'] = {}
        type_obj = objects.InstanceType(self.context, **inst_type)
        type_obj.create(self.context)
        return type_obj

    @mock.patch('mogan.engine.api.API._check_requested_networks')
    def test__validate_and_build_base_options(self, mock_check_nets):
        instance_type = self._create_instance_type()
        mock_check_nets.return_value = 3

        base_opts, max_network_count = \
            self.engine_api._validate_and_build_base_options(
                self.context,
                instance_type=instance_type,
                image_uuid='fake-uuid',
                name='fake-name',
                description='fake-descritpion',
                availability_zone='test_az',
                extra={'k1', 'v1'},
                requested_networks=None,
                max_count=2)

        self.assertEqual('fake-user', base_opts['user_id'])
        self.assertEqual('fake-project', base_opts['project_id'])
        self.assertEqual(states.BUILDING, base_opts['status'])
        self.assertEqual(instance_type.uuid, base_opts['instance_type_uuid'])
        self.assertEqual({'k1', 'v1'}, base_opts['extra'])
        self.assertEqual('test_az', base_opts['availability_zone'])

    @mock.patch.object(objects.Instance, 'create')
    def test__provision_instances(self, mock_inst_create):
        mock_inst_create.return_value = mock.MagicMock()

        base_options = {'image_uuid': 'fake-uuid',
                        'status': states.BUILDING,
                        'user_id': 'fake-user',
                        'project_id': 'fake-project',
                        'instance_type_uuid': 'fake-type-uuid',
                        'name': 'fake-name',
                        'description': 'fake-description',
                        'extra': {},
                        'availability_zone': None}
        min_count = 1
        max_count = 2
        self.engine_api._provision_instances(self.context, base_options,
                                             min_count, max_count)
        calls = [mock.call() for i in range(max_count)]
        mock_inst_create.assert_has_calls(calls)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'create_instance')
    @mock.patch('mogan.engine.api.API._provision_instances')
    @mock.patch('mogan.engine.api.API._get_image')
    @mock.patch('mogan.engine.api.API._validate_and_build_base_options')
    @mock.patch.object(engine_rpcapi.EngineAPI, 'list_availability_zones')
    def test_create(self, mock_list_az, mock_validate, mock_get_image,
                    mock_provision, mock_create):
        instance_type = self._create_instance_type()

        base_options = {'image_uuid': 'fake-uuid',
                        'status': states.BUILDING,
                        'user_id': 'fake-user',
                        'project_id': 'fake-project',
                        'instance_type_uuid': 'fake-type-uuid',
                        'name': 'fake-name',
                        'description': 'fake-description',
                        'extra': {'k1', 'v1'},
                        'availability_zone': 'test_az'}
        min_count = 1
        max_count = 2
        mock_validate.return_value = (base_options, max_count)
        mock_get_image.side_effect = None
        mock_provision.return_value = [mock.MagicMock()
                                       for i in range(max_count)]
        mock_create.return_value = mock.MagicMock()
        mock_list_az.return_value = {'availability_zones': ['test_az']}
        requested_networks = [{'uuid': 'fake'}]
        before_quotas = {}
        res = self.dbapi.quota_get_all_by_project(self.context,
                                                  self.project_id)
        for p_quota in res:
            before_quotas[p_quota.resource_name] = p_quota.allocated

        self.engine_api.create(
            self.context,
            instance_type=instance_type,
            image_uuid='fake-uuid',
            name='fake-name',
            description='fake-descritpion',
            availability_zone='test_az',
            extra={'k1', 'v1'},
            requested_networks=requested_networks,
            min_count=min_count,
            max_count=max_count)

        mock_list_az.assert_called_once_with(self.context)
        mock_validate.assert_called_once_with(
            self.context, instance_type, 'fake-uuid', 'fake-name',
            'fake-descritpion', 'test_az', {'k1', 'v1'}, requested_networks,
            max_count)
        mock_provision.assert_called_once_with(self.context, base_options,
                                               min_count, max_count)
        self.assertTrue(mock_create.called)
        self.assertTrue(mock_get_image.called)
        res = self.dbapi.quota_get_all_by_project(self.context,
                                                  self.project_id)
        after_quotas = {}
        for p_quota in res:
            after_quotas[p_quota.resource_name] = p_quota.allocated
        self.assertEqual(before_quotas.get('instances', 0) + 1,
                         after_quotas.get('instances'))

    @mock.patch.object(engine_rpcapi.EngineAPI, 'list_availability_zones')
    def test_create_with_invalid_az(self, mock_list_az):
        instance_type = mock.MagicMock()
        mock_list_az.return_value = {'availability_zones': ['invalid_az']}

        self.assertRaises(
            exception.AZNotFound,
            self.engine_api.create,
            self.context,
            instance_type,
            'fake-uuid',
            'fake-name',
            'fake-descritpion',
            'test_az',
            {'k1', 'v1'},
            [{'uuid': 'fake'}])

        mock_list_az.assert_called_once_with(self.context)

    def _create_fake_instance_obj(self, fake_instance):
        fake_instance_obj = objects.Instance(self.context, **fake_instance)
        fake_instance_obj.create(self.context)
        return fake_instance_obj

    def test_lock_by_owner(self):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id)
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.engine_api.lock(self.context, fake_instance_obj)
        self.assertTrue(fake_instance_obj.locked)
        self.assertEqual('owner', fake_instance_obj.locked_by)

    def test_unlock_by_owner(self):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.engine_api.unlock(self.context, fake_instance_obj)
        self.assertFalse(fake_instance_obj.locked)
        self.assertEqual(None, fake_instance_obj.locked_by)

    def test_lock_by_admin(self):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id)
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        admin_context = context.get_admin_context()
        self.engine_api.lock(admin_context, fake_instance_obj)
        self.assertTrue(fake_instance_obj.locked)
        self.assertEqual('admin', fake_instance_obj.locked_by)

    def test_unlock_by_admin(self):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        admin_context = context.get_admin_context()
        self.engine_api.unlock(admin_context, fake_instance_obj)
        self.assertFalse(fake_instance_obj.locked)
        self.assertEqual(None, fake_instance_obj.locked_by)

    @mock.patch('mogan.engine.api.API._delete_instance')
    def test_delete_locked_instance_with_non_admin(self, mock_deleted):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.assertRaises(exception.InstanceIsLocked,
                          self.engine_api.delete,
                          self.context, fake_instance_obj)
        self.assertFalse(mock_deleted.called)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'set_power_state')
    def test_power_locked_instance_with_non_admin(self, mock_powered):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.assertRaises(exception.InstanceIsLocked,
                          self.engine_api.power,
                          self.context, fake_instance_obj, 'reboot')
        self.assertFalse(mock_powered.called)

    @mock.patch('mogan.engine.api.API._delete_instance')
    def test_delete_locked_instance_with_admin(self, mock_deleted):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        admin_context = context.get_admin_context()
        self.engine_api.delete(admin_context, fake_instance_obj)
        self.assertTrue(mock_deleted.called)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'set_power_state')
    def test_power_locked_instance_with_admin(self, mock_powered):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        admin_context = context.get_admin_context()
        self.engine_api.power(admin_context, fake_instance_obj, 'reboot')
        self.assertTrue(mock_powered.called)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'rebuild_instance')
    def test_rebuild_locked_instance_with_non_admin(self, mock_rebuild):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.assertRaises(exception.InstanceIsLocked,
                          self.engine_api.rebuild,
                          self.context, fake_instance_obj)
        self.assertFalse(mock_rebuild.called)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'rebuild_instance')
    def test_rebuild_locked_instance_with_admin(self, mock_rebuild):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id,
            locked=True, locked_by='owner')
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        admin_context = context.get_admin_context()
        self.engine_api.rebuild(admin_context, fake_instance_obj)
        self.assertTrue(mock_rebuild.called)

    @mock.patch.object(engine_rpcapi.EngineAPI, 'rebuild_instance')
    def test_rebuild_instance(self, mock_rebuild):
        fake_instance = db_utils.get_test_instance(
            user_id=self.user_id, project_id=self.project_id)
        fake_instance_obj = self._create_fake_instance_obj(fake_instance)
        self.engine_api.rebuild(self.context, fake_instance_obj)
        self.assertTrue(mock_rebuild.called)
