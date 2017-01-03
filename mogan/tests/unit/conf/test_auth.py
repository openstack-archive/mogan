# Copyright 2016 Mirantis Inc
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

from keystoneauth1 import identity as kaidentity
from keystoneauth1 import loading as kaloading
from oslo_config import cfg

from mogan.conf import auth as nimble_auth
from mogan.tests import base


class AuthConfTestCase(base.TestCase):

    def setUp(self):
        super(AuthConfTestCase, self).setUp()
        self.config(region_name='fake_region',
                    group='keystone')
        self.test_group = 'test_group'
        self.cfg_fixture.conf.register_group(cfg.OptGroup(self.test_group))
        nimble_auth.register_auth_opts(self.cfg_fixture.conf, self.test_group)
        self.config(auth_type='password',
                    group=self.test_group)
        # NOTE(pas-ha) this is due to auth_plugin options
        # being dynamically registered on first load,
        # but we need to set the config before
        plugin = kaloading.get_plugin_loader('password')
        opts = kaloading.get_auth_plugin_conf_options(plugin)
        self.cfg_fixture.register_opts(opts, group=self.test_group)
        self.config(auth_url='http://127.0.0.1:9898',
                    username='fake_user',
                    password='fake_pass',
                    project_name='fake_tenant',
                    group=self.test_group)

    def test_add_auth_opts(self):
        opts = nimble_auth.add_auth_opts([])
        # check that there is no duplicates
        names = {o.dest for o in opts}
        self.assertEqual(len(names), len(opts))
        # NOTE(pas-ha) checking for most standard auth and session ones only
        expected = {'timeout', 'insecure', 'cafile', 'certfile', 'keyfile',
                    'auth_type', 'auth_url', 'username', 'password',
                    'tenant_name', 'project_name', 'trust_id',
                    'domain_id', 'user_domain_id', 'project_domain_id'}
        self.assertTrue(expected.issubset(names))

    def test_load_auth(self):
        auth = nimble_auth.load_auth(self.cfg_fixture.conf, self.test_group)
        # NOTE(pas-ha) 'password' auth_plugin is used
        self.assertIsInstance(auth, kaidentity.generic.password.Password)
        self.assertEqual('http://127.0.0.1:9898', auth.auth_url)

    def test_load_auth_missing_options(self):
        # NOTE(pas-ha) 'password' auth_plugin is used,
        # so when we set the required auth_url to None,
        # MissingOption is raised
        self.config(auth_url=None, group=self.test_group)
        self.assertIsNone(nimble_auth.load_auth(
            self.cfg_fixture.conf, self.test_group))
