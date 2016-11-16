#
# Copyright 2016 Huawei Technologies Co., Ltd.
#
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
import six

from nimble.common import ironic
from nimble.engine import rpcapi
from nimble.tests.functional.api import v1 as v1_test


class TestInstances(v1_test.APITestV1):
    INSTANCE_TYPE_UUID = 'ff28b5a2-73e5-431c-b4b7-1b96b74bca7b'

    INSTANCE_UUIDS = ['59f1b681-6ca4-4a17-b784-297a7285004e',
                      '2b32fc87-576c-481b-880e-bef8c7351746',
                      '482decff-7561-41ad-9bfb-447265b26972',
                      '427693e1-a820-4d7d-8a92-9f5fe2849399']

    def setUp(self):
        super(TestInstances, self).setUp()
        self._prepare_instance_type()

    def _make_app(self):
        return super(TestInstances, self)._make_app()

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_instance_type(self, mocked):
        mocked.side_effect = [self.INSTANCE_TYPE_UUID]
        body = {"name": "type_for_instance_testing",
                "description": "type for instance testing"}
        self.post_json('/types', body, status=201)

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_instance(self, amount, mocked):
        mocked.side_effect = self.INSTANCE_UUIDS[:amount]
        responses = []
        for i in six.moves.xrange(amount):
            test_body = {
                "name": "test_instance_" + str(i),
                "description": "just test instance " + str(i),
                'instance_type_uuid': 'ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                'image_uuid': 'b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                'availability_zone': 'test_zone',
                'networks': [{'uuid': 'c1940655-8b8e-4370-b8f9-03ba1daeca31'}],
                'extra': {'fake_key': 'fake_value'}
            }
            responses.append(
                self.post_json('/instances', test_body, status=201))
        return responses

    @mock.patch.object(rpcapi, 'EngineAPI', mock.MagicMock())
    def test_instance_post(self):
        resp = self._prepare_instance(1)[0]
        self.assertEqual('test_instance_0', resp['name'])
        self.assertEqual('just test instance 0', resp['description'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resp['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resp['image_uuid'])
        self.assertEqual('test_zone', resp['availability_zone'])
        self.assertEqual({}, resp['network_info'])
        self.assertEqual({'fake_key': 'fake_value'}, resp['extra'])

    @mock.patch.object(rpcapi, 'EngineAPI', mock.MagicMock())
    @mock.patch.object(ironic, 'IronicClientWrapper')
    def test_instance_show(self, mocked):
        mocked_ironic = mock.MagicMock()
        mocked.return_value = mocked_ironic
        mock_node = mock.MagicMock()
        mocked_ironic.call.return_value = mock_node
        mock_node.power_state = 'power on'
        self._prepare_instance(1)
        resp = self.get_json('/instances/59f1b681-6ca4-4a17-b784-297a7285004e')
        self.assertEqual('test_instance_0', resp['name'])
        self.assertEqual('just test instance 0', resp['description'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resp['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resp['image_uuid'])
        self.assertEqual('test_zone', resp['availability_zone'])
        self.assertEqual({}, resp['network_info'])
        self.assertEqual({'fake_key': 'fake_value'}, resp['extra'])
        # TODO(liusheng) the instance show has been broken by:
        # https://review.openstack.org/#/c/398924/, need to wait fix.
        # self.assertEqual('power on', resp['power_state'])

    @mock.patch.object(rpcapi, 'EngineAPI', mock.MagicMock())
    def test_instance_list(self):
        self._prepare_instance(4)
        resps = self.get_json('/instances')['instances']
        self.assertEqual(4, len(resps))
        self.assertEqual('test_instance_0', resps[0]['name'])
        self.assertEqual('just test instance 0', resps[0]['description'])
        self.assertEqual(None, resps[0]['status'])

    @mock.patch.object(rpcapi, 'EngineAPI', mock.MagicMock())
    def test_instance_list_with_details(self):
        self._prepare_instance(4)
        resps = self.get_json('/instances/detail')['instances']
        self.assertEqual(4, len(resps))
        self.assertEqual('test_instance_0', resps[0]['name'])
        self.assertEqual('just test instance 0', resps[0]['description'])
        self.assertEqual(None, resps[0]['status'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resps[0]['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resps[0]['image_uuid'])

    @mock.patch.object(rpcapi, 'EngineAPI', mock.MagicMock())
    def test_instance_delete(self):
        resps = self._prepare_instance(4)
        self.assertEqual(4, len(resps))
        self.delete('/instances/' + self.INSTANCE_UUIDS[0], status=204)
        # NOTE(liusheng): Since the instance deletion is a synchronized call
        # and the real deletion will be done in nimble-engine, here we have
        # mocked the rpc call, so we cannot confirm the amount of instance
        # after deletion
        # resps = self.get_json('/instances')['instances']
        # self.assertEqual(3, len(resps))
