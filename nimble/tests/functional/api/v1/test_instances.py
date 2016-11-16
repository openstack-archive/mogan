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
from nimble.engine import api as engine_api
from nimble.tests.functional.api import v1 as v1_test

FAKE_IMAGE = type(
    'Image', (object,),
    {u'status': u'active',
     u'tags': [],
     u'kernel_id': u'fd24d91a-dfd5-4a3c-b990-d4563eb27396',
     u'container_format': u'ami',
     u'min_ram': 0,
     u'ramdisk_id': u'd629522b-ebaa-4c92-9514-9e31fe760d18',
     u'updated_at': u'2016-06-20T13: 34: 41Z',
     u'visibility': u'public',
     u'owner': u'6824974c08974d4db864bbaa6bc08303',
     u'file': u'/v2/images/fda54a44-3f96-40bf-ab07-0a4ce9e1761d/file',
     u'min_disk': 0,
     u'virtual_size': None,
     u'id': u'b8f82429-3a13-4ffe-9398-4d1abdc256a8',
     u'size': 25165824,
     u'name': u'cirros-0.3.4-x86_64-uec',
     u'checksum': u'eb9139e4942121f22bbc2afc0400b2a4',
     u'created_at': u'2016-06-20T13: 34: 40Z',
     u'disk_format': u'ami',
     u'protected': False,
     u'schema': u'/v2/schemas/image'})

FAKE_NODE = {
    u'instance_uuid': u'dc18e1a6-4177-4b64-8a00-1974696dd049',
    u'power_state': u'power on',
    u'links': [{
        u'href': u'http: //10.3.150.100: 6385/v1/nodes/3b8b50e2-f29'
                 u'2-45a7-a587-89ad35aa888b',
        u'rel': u'self'
    },
        {
            u'href': u'http: //10.3.150.100: 6385/nodes/3b8b50e2-f292-45a'
                     u'7-a587-89ad35aa888b',
            u'rel': u'bookmark'
        }]
}


class TestInstances(v1_test.APITestV1):
    INSTANCE_TYPE_UUID = 'ff28b5a2-73e5-431c-b4b7-1b96b74bca7b'

    INSTANCE_UUIDS = ['59f1b681-6ca4-4a17-b784-297a7285004e',
                      '2b32fc87-576c-481b-880e-bef8c7351746',
                      '482decff-7561-41ad-9bfb-447265b26972',
                      '427693e1-a820-4d7d-8a92-9f5fe2849399']

    @mock.patch('nimble.engine.rpcapi.EngineAPI')
    @mock.patch('nimble.image.api.API')
    def setUp(self, mocked_image, mocked_rpc):
        self.mocked_image = mock.MagicMock()
        mocked_image.return_value = self.mocked_image
        self.mocked_rpc = mock.MagicMock()
        mocked_rpc.return_value = self.mocked_rpc

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

    def test_instance_post(self):
        self.mocked_image.get.return_value = FAKE_IMAGE
        resp = self._prepare_instance(1)[0].json
        self.assertEqual('test_instance_0', resp['name'])
        self.assertEqual('building', resp['status'])
        self.assertEqual('59f1b681-6ca4-4a17-b784-297a7285004e',
                         resp['uuid'])
        self.assertEqual('just test instance 0', resp['description'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resp['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resp['image_uuid'])
        self.assertEqual('test_zone', resp['availability_zone'])
        self.assertEqual({}, resp['network_info'])
        self.assertEqual({'fake_key': 'fake_value'}, resp['extra'])
        self.assertIn('links', resp)
        self.assertIn('created_at', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('network_info', resp)
        self.assertIn('project_id', resp)
        self.assertIn('launched_at', resp)

    def test_instance_show(self):
        self.mocked_image.get.return_value = FAKE_IMAGE
        self.mocked_rpc.get_ironic_node.return_value = FAKE_NODE
        self._prepare_instance(1)
        resp = self.get_json('/instances/59f1b681-6ca4-4a17-b784-297a7285004e')
        self.assertEqual('test_instance_0', resp['name'])
        self.assertEqual('building', resp['status'])
        self.assertEqual('59f1b681-6ca4-4a17-b784-297a7285004e',
                         resp['uuid'])
        self.assertEqual('just test instance 0', resp['description'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resp['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resp['image_uuid'])
        self.assertEqual('test_zone', resp['availability_zone'])
        self.assertEqual({}, resp['network_info'])
        self.assertEqual({'fake_key': 'fake_value'}, resp['extra'])
        self.assertIn('links', resp)
        self.assertIn('created_at', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('network_info', resp)
        self.assertIn('project_id', resp)
        self.assertIn('launched_at', resp)

    def test_instance_list(self):
        self.mocked_image.get.side_effects = [
            FAKE_IMAGE, FAKE_IMAGE, FAKE_IMAGE, FAKE_IMAGE]
        self._prepare_instance(4)
        resps = self.get_json('/instances')['instances']
        self.assertEqual(4, len(resps))
        self.assertEqual('test_instance_0', resps[0]['name'])
        self.assertEqual('just test instance 0', resps[0]['description'])
        self.assertEqual('building', resps[0]['status'])

    def test_instance_list_with_details(self):
        self.mocked_image.get.side_effects = [
            FAKE_IMAGE, FAKE_IMAGE, FAKE_IMAGE, FAKE_IMAGE]
        self._prepare_instance(4)
        resps = self.get_json('/instances/detail')['instances']
        self.assertEqual(4, len(resps))
        self.assertEqual('test_instance_0', resps[0]['name'])
        self.assertEqual('just test instance 0', resps[0]['description'])
        self.assertEqual('building', resps[0]['status'])
        self.assertEqual('ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                         resps[0]['instance_type_uuid'])
        self.assertEqual('b8f82429-3a13-4ffe-9398-4d1abdc256a8',
                         resps[0]['image_uuid'])

    def test_instance_delete(self):
        self.mocked_image.get.return_value = FAKE_IMAGE
        self._prepare_instance(1)
        self.delete('/instances/' + self.INSTANCE_UUIDS[0], status=204)
        # NOTE(liusheng): Since the instance deletion is a synchronized call
        # and the real deletion will be done in nimble-engine, here we have
        # mocked the rpc call, so we cannot confirm the amount of instance
        # after deletion
        # resps = self.get_json('/instances')['instances']
        # self.assertEqual(3, len(resps))
