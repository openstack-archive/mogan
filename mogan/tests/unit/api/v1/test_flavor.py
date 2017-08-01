#
# Copyright 2016 Intel
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

from mogan.tests.functional.api import v1 as v1_test
from mogan.tests.unit.db import utils


class TestServerAuthorization(v1_test.APITestV1):

    def setUp(self):
        super(TestServerAuthorization, self).setUp()
        self.flavor = utils.create_test_flavor(name="test_flavor")

    def test_server_get_one_by_no_admin(self):
        # role is not admin, he can't get schedule info
        headers = self.gen_headers(self.context, roles="no-admin")
        resp = self.get_json('/flavors/%s' % self.flavor.uuid,
                             headers=headers)
        self.assertIn('name', resp)
        self.assertIn('uuid', resp)
        self.assertIn('is_public', resp)
        self.assertIn('description', resp)
        self.assertIn('links', resp)
        self.assertNotIn('resources', resp)
        self.assertNotIn('resource_traits', resp)

    def test_server_get_one_by_admin(self):
        # role is admin, he can get everything.
        headers = self.gen_headers(self.context, roles="admin")
        resp = self.get_json('/flavors/%s' % self.flavor.uuid,
                             headers=headers)
        self.assertIn('name', resp)
        self.assertIn('uuid', resp)
        self.assertIn('is_public', resp)
        self.assertIn('description', resp)
        self.assertIn('links', resp)
        self.assertIn('resources', resp)
        self.assertIn('resource_traits', resp)
