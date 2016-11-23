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

from nimble.common import context
from nimble.engine import api as engine_api
from nimble.engine import rpcapi as engine_rpcapi
from nimble.engine import status
from nimble import objects
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils as db_utils


class ComputeAPIUnitTest(base.DbTestCase):
    def setUp(self):
        super(ComputeAPIUnitTest, self).setUp()
        self.user_id = 'fake-user'
        self.project_id = 'fake-project'
        self.engine_api = engine_api.API()
        self.context = context.RequestContext(user_id=self.user_id,
                                              project_id=self.project_id)

    def _create_instance_type(self):
        inst_type = db_utils.get_test_instance_type()
        inst_type['extra'] = {}
        type_obj = objects.InstanceType(self.context, **inst_type)
        type_obj.create(self.context)
        return type_obj

    def test__validate_and_build_base_options(self):
        instance_type = self._create_instance_type()

        base_opts = self.engine_api._validate_and_build_base_options(
            self.context,
            instance_type=instance_type,
            image_uuid='fake-uuid',
            name='fake-name',
            description='fake-descritpion',
            availability_zone='test_az',
            extra={'k1', 'v1'})

        self.assertEqual('fake-user', base_opts['user_id'])
        self.assertEqual('fake-project', base_opts['project_id'])
        self.assertEqual(status.BUILDING, base_opts['status'])
        self.assertEqual(instance_type.uuid, base_opts['instance_type_uuid'])
        self.assertEqual({'k1', 'v1'}, base_opts['extra'])
        self.assertEqual('test_az', base_opts['availability_zone'])

    @mock.patch.object(objects.Instance, 'create')
    def test__provision_instances(self, mock_inst_create):
        mock_inst_create.return_value = mock.MagicMock()

        base_options = {'image_uuid': 'fake-uuid',
                        'status': status.BUILDING,
                        'user_id': 'fake-user',
                        'project_id': 'fake-project',
                        'instance_type_uuid': 'fake-type-uuid',
                        'name': 'fake-name',
                        'description': 'fake-description',
                        'extra': {},
                        'availability_zone': None}

        self.engine_api._provision_instances(self.context, base_options)
        mock_inst_create.assert_called_once_with()

    @mock.patch.object(engine_rpcapi.EngineAPI, 'create_instance')
    @mock.patch('nimble.engine.api.API._provision_instances')
    @mock.patch('nimble.engine.api.API._get_image')
    @mock.patch('nimble.engine.api.API._validate_and_build_base_options')
    def test_create(self, mock_validate, mock_get_image,
                    mock_provision, mock_create):
        instance_type = self._create_instance_type()

        base_options = {'image_uuid': 'fake-uuid',
                        'status': status.BUILDING,
                        'user_id': 'fake-user',
                        'project_id': 'fake-project',
                        'instance_type_uuid': 'fake-type-uuid',
                        'name': 'fake-name',
                        'description': 'fake-description',
                        'extra': {'k1', 'v1'},
                        'availability_zone': None}
        mock_validate.return_value = base_options
        mock_get_image.side_effect = None
        mock_create.return_value = mock.MagicMock()

        self.engine_api.create(
            self.context,
            instance_type=instance_type,
            image_uuid='fake-uuid',
            name='fake-name',
            description='fake-descritpion',
            availability_zone='test_az',
            extra={'k1', 'v1'},
            requested_networks=[{'uuid': 'fake'}])

        mock_validate.assert_called_once_with(
            self.context, instance_type, 'fake-uuid', 'fake-name',
            'fake-descritpion', 'test_az', {'k1', 'v1'})
        mock_provision.assert_called_once_with(self.context, base_options)
        self.assertTrue(mock_create.called)
        self.assertTrue(mock_get_image.called)
