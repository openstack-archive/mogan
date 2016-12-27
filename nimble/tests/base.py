# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
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

import datetime
import mock
import os

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_context import context
from oslo_db import options
from oslo_log import log
from oslo_serialization import jsonutils
from oslotest import base
import pecan
import six
import testscenarios
import testtools

from nimble.common import config as nimble_config
from nimble.tests import policy_fixture


CONF = cfg.CONF
options.set_defaults(cfg.CONF)
try:
    log.register_options(CONF)
except cfg.ArgsAlreadyParsedError:
    pass


class BaseTestCase(testscenarios.WithScenarios, base.BaseTestCase):
    """Test base class."""

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.addCleanup(CONF.reset)


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.context = context.get_admin_context()

        self._set_config()

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)
        self.policy = self.useFixture(policy_fixture.PolicyFixture())

    def _set_config(self):
        self.cfg_fixture = self.useFixture(config_fixture.Config(cfg.CONF))
        self.config(use_stderr=False,
                    fatal_exception_format_errors=True)
        self.set_defaults(host='fake-mini',
                          debug=True)
        self.set_defaults(connection="sqlite://",
                          sqlite_synchronous=False,
                          group='database')
        CONF.set_override('glance_api_servers', 'fake-glance', 'glance')
        nimble_config.parse_args([], default_config_files=[])

    def config(self, **kw):
        """Override config options for a test."""
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group, enforce_type=True)

    def set_defaults(self, **kw):
        """Set default values of config options."""
        group = kw.pop('group', None)
        for o, v in kw.items():
            self.cfg_fixture.set_default(o, v, group=group)

    def get_path(self, project_file=None):
        """Get the absolute path to a file. Used for testing the API.

        :param project_file: File whose path to return. Default: None.
        :returns: path to the specified file, or path to project root.
        """
        root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..',
                                            '..',
                                            )
                               )
        if project_file:
            return os.path.join(root, project_file)
        else:
            return root

    def mock_object(self, obj, attr_name, *args, **kwargs):
        """Use python mock to mock an object attribute

        Mocks the specified objects attribute with the given value.
        Automatically performs 'addCleanup' for the mock.

        """
        patcher = mock.patch.object(obj, attr_name, *args, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def override_config(self, name, override, group=None):
        """Cleanly override CONF variables."""
        CONF.set_override(name, override, group)
        self.addCleanup(CONF.clear_override, name, group)

    def flags(self, **kw):
        """Override CONF variables for a test."""
        for k, v in kw.items():
            self.override_config(k, v)

    def assertJsonEqual(self, expected, observed):
        """Asserts that 2 complex data structures are json equivalent.

        We use data structures which serialize down to json throughout
        the code, and often times we just need to know that these are
        json equivalent. This means that list order is not important,
        and should be sorted.

        Because this is a recursive set of assertions, when failure
        happens we want to expose both the local failure and the
        global view of the 2 data structures being compared. So a
        MismatchError which includes the inner failure as the
        mismatch, and the passed in expected / observed as matchee /
        matcher.

        """
        if isinstance(expected, six.string_types):
            expected = jsonutils.loads(expected)
        if isinstance(observed, six.string_types):
            observed = jsonutils.loads(observed)

        def sort_key(x):
            if isinstance(x, (set, list)) or isinstance(x, datetime.datetime):
                return str(x)
            if isinstance(x, dict):
                items = ((sort_key(key), sort_key(value))
                         for key, value in x.items())
                return sorted(items)
            return x

        def inner(expected, observed):
            if isinstance(expected, dict) and isinstance(observed, dict):
                self.assertEqual(len(expected), len(observed))
                expected_keys = sorted(expected)
                observed_keys = sorted(observed)
                self.assertEqual(expected_keys, observed_keys)

                for key in list(six.iterkeys(expected)):
                    inner(expected[key], observed[key])
            elif (isinstance(expected, (list, tuple, set)) and
                  isinstance(observed, (list, tuple, set))):
                self.assertEqual(len(expected), len(observed))

                expected_values_iter = iter(sorted(expected, key=sort_key))
                observed_values_iter = iter(sorted(observed, key=sort_key))

                for i in range(len(expected)):
                    inner(next(expected_values_iter),
                          next(observed_values_iter))
            else:
                self.assertEqual(expected, observed)

        try:
            inner(expected, observed)
        except testtools.matchers.MismatchError as e:
            inner_mismatch = e.mismatch
            # inverting the observed / expected because testtools
            # error messages assume expected is second. Possibly makes
            # reading the error messages less confusing.
            raise testtools.matchers.MismatchError(
                observed, expected, inner_mismatch, verbose=True)
