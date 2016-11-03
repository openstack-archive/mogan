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

import os

import fixtures
from oslo_config import cfg
from oslo_policy import opts as policy_opts

from nimble.common import policy as nimble_policy

CONF = cfg.CONF

# NOTE(deva): We ship a default that always masks passwords, but for testing
#             we need to override that default to ensure passwords can be
#             made visible by operators that choose to do so.
policy_data = """
{
    "show_password": "tenant:admin"
}
"""


class PolicyFixture(fixtures.Fixture):
    def setUp(self):
        super(PolicyFixture, self).setUp()
        self.policy_dir = self.useFixture(fixtures.TempDir())
        self.policy_file_name = os.path.join(self.policy_dir.path,
                                             'policy.json')
        with open(self.policy_file_name, 'w') as policy_file:
            policy_file.write(policy_data)
        policy_opts.set_defaults(CONF)
        CONF.set_override('policy_file', self.policy_file_name, 'oslo_policy')
        nimble_policy._ENFORCER = None
        self.addCleanup(nimble_policy.get_enforcer().clear)
