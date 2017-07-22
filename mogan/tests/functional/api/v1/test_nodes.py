# Copyright 2017 Huawei Technologies Co., Ltd.
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

from mogan.tests.functional.api import v1 as v1_test


class TestNode(v1_test.APITestV1):

    def setUp(self):
        super(TestNode, self).setUp()

    @mock.patch('mogan.engine.rpcapi.EngineAPI.list_compute_nodes')
    def test_node_get_all(self, get_nodes):
        get_nodes.return_value = {'nodes': ['node-0', 'node-1']}
        headers = self.gen_headers(self.context, roles="admin")
        resp = self.get_json('/nodes', headers=headers)
        self.assertItemsEqual(['node-0', 'node-1'], resp['nodes'])
