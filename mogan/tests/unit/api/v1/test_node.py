#
# Copyright 2018 Fiberhome
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


class TestNodeAuthorization(v1_test.APITestV1):

    def setUp(self):
        super(TestNodeAuthorization, self).setUp()

    @mock.patch('mogan.engine.api.API.list_compute_nodes')
    def test_get_nodes_by_admin(self, mock_list):
        mock_list.return_value = {'nodes': ['node1', 'node2']}
        headers = self.gen_headers(self.context, roles="admin")
        resp = self.get_json('/nodes', headers=headers)
        self.assertItemsEqual(['node1', 'node2'], resp['nodes'])
