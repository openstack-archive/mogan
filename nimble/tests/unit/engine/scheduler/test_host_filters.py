# Copyright 2011 OpenStack Foundation  # All Rights Reserved.
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
"""
Tests For Scheduler Node Filters.
"""

import ddt
import mock
from oslo_serialization import jsonutils
from requests import exceptions as request_exceptions

from nimble.common import context
from nimble import db
from nimble.common import exception
from nimble.engine.scheduler import filters
from nimble.engine.scheduler.filters import extra_specs_ops
from nimble.tests import base as test
from nimble.tests.unit.engine.scheduler import fakes
from nimble.tests.unit import fake_constants
#from cinder.tests.unit import utils


class NodeFiltersTestCase(test.TestCase):
    """Test case for node filters."""

    def setUp(self):
        super(NodeFiltersTestCase, self).setUp()
        self.context = context.RequestContext(fake_constants.USER_ID, fake_constants.PROJECT_ID)
        # This has a side effect of testing 'get_filter_classes'
        # when specifying a method (in this case, our standard filters)
        filter_handler = filters.NodeFilterHandler('nimble.engine.scheduler.filters')
        classes = filter_handler.get_all_classes()
        self.class_map = {}
        for cls in classes:
            self.class_map[cls.__name__] = cls


@ddt.ddt
class CapacityFilterTestCase(NodeFiltersTestCase):
    def setUp(self):
        super(CapacityFilterTestCase, self).setUp()
        self.json_query = jsonutils.dumps(
            ['and',
                ['>=', '$free_capacity_gb', 1024],
                ['>=', '$total_capacity_gb', 10 * 1024]])

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_passes(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_current_node_passes(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100, 'vol_exists_on': 'node1'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 100,
                                    'free_capacity_gb': 10,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_fails(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 200,
                                    'free_capacity_gb': 120,
                                    'reserved_percentage': 20,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_fails_free_capacity_None(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': None,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_passes_infinite(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': 'infinite',
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_passes_unknown(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': 'unknown',
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_passes_total_infinite(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': 'infinite',
                                    'total_capacity_gb': 'infinite',
                                    'reserved_percentage': 0,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_passes_total_unknown(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': 'unknown',
                                    'total_capacity_gb': 'unknown',
                                    'reserved_percentage': 0,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_fails_total_infinite(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 'infinite',
                                    'reserved_percentage': 5,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_fails_total_unknown(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 'unknown',
                                    'reserved_percentage': 5,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_fails_total_zero(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 0,
                                    'reserved_percentage': 5,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_thin_true_passes(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'provisioned_capacity_gb': 500,
                                    'max_over_subscription_ratio': 2.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_thin_true_passes2(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 3000,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'provisioned_capacity_gb': 7000,
                                    'max_over_subscription_ratio': 20,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_thin_false_passes(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> False',
                             'capabilities:thick_provisioning_support':
                                 '<is> True'}
        service = {'disabled': False}
        # If "thin_provisioning_support" is False,
        # "max_over_subscription_ratio" will be ignored.
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'provisioned_capacity_gb': 300,
                                    'max_over_subscription_ratio': 1.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': False,
                                    'thick_provisioning_support': True,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_over_subscription_less_than_1(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 200,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 100,
                                    'provisioned_capacity_gb': 400,
                                    'max_over_subscription_ratio': 0.8,
                                    'reserved_percentage': 0,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_over_subscription_equal_to_1(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 150,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'provisioned_capacity_gb': 400,
                                    'max_over_subscription_ratio': 1.0,
                                    'reserved_percentage': 0,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_over_subscription_fails(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 200,
                                    'provisioned_capacity_gb': 700,
                                    'max_over_subscription_ratio': 1.5,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_over_subscription_fails2(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 2000,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 30,
                                    'provisioned_capacity_gb': 9000,
                                    'max_over_subscription_ratio': 20,
                                    'reserved_percentage': 0,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_reserved_thin_true_fails(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> False'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 100,
                                    'provisioned_capacity_gb': 1000,
                                    'max_over_subscription_ratio': 2.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': False,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_reserved_thin_false_fails(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> False',
                             'capabilities:thick_provisioning_support':
                                 '<is> True'}
        service = {'disabled': False}
        # If "thin_provisioning_support" is False,
        # "max_over_subscription_ratio" will be ignored.
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 100,
                                    'provisioned_capacity_gb': 400,
                                    'max_over_subscription_ratio': 1.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': False,
                                    'thick_provisioning_support': True,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_reserved_thin_thick_true_fails(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> True'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 0,
                                    'provisioned_capacity_gb': 800,
                                    'max_over_subscription_ratio': 2.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': True,
                                    'updated_at': None,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    @mock.patch('cinder.utils.service_is_up')
    def test_filter_reserved_thin_thick_true_passes(self, _mock_serv_is_up):
        _mock_serv_is_up.return_value = True
        filt_cls = self.class_map['CapacityFilter']()
        filter_properties = {'size': 100,
                             'capabilities:thin_provisioning_support':
                                 '<is> True',
                             'capabilities:thick_provisioning_support':
                                 '<is> True'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'total_capacity_gb': 500,
                                    'free_capacity_gb': 125,
                                    'provisioned_capacity_gb': 400,
                                    'max_over_subscription_ratio': 2.0,
                                    'reserved_percentage': 5,
                                    'thin_provisioning_support': True,
                                    'thick_provisioning_support': True,
                                    'updated_at': None,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))


class TestFilter(filters.BaseNodeFilter):
    pass


class TestBogusFilter(object):
    """Class that doesn't inherit from BaseNodeFilter."""
    pass


class ExtraSpecsOpsTestCase(test.TestCase):
    def _do_extra_specs_ops_test(self, value, req, matches):
        assertion = self.assertTrue if matches else self.assertFalse
        assertion(extra_specs_ops.match(value, req))

    def test_extra_specs_matches_simple(self):
        self._do_extra_specs_ops_test(
            value='1',
            req='1',
            matches=True)

    def test_extra_specs_fails_simple(self):
        self._do_extra_specs_ops_test(
            value='',
            req='1',
            matches=False)

    def test_extra_specs_fails_simple2(self):
        self._do_extra_specs_ops_test(
            value='3',
            req='1',
            matches=False)

    def test_extra_specs_fails_simple3(self):
        self._do_extra_specs_ops_test(
            value='222',
            req='2',
            matches=False)

    def test_extra_specs_fails_with_bogus_ops(self):
        self._do_extra_specs_ops_test(
            value='4',
            req='> 2',
            matches=False)

    def test_extra_specs_matches_with_op_eq(self):
        self._do_extra_specs_ops_test(
            value='123',
            req='= 123',
            matches=True)

    def test_extra_specs_matches_with_op_eq2(self):
        self._do_extra_specs_ops_test(
            value='124',
            req='= 123',
            matches=True)

    def test_extra_specs_fails_with_op_eq(self):
        self._do_extra_specs_ops_test(
            value='34',
            req='= 234',
            matches=False)

    def test_extra_specs_fails_with_op_eq3(self):
        self._do_extra_specs_ops_test(
            value='34',
            req='=',
            matches=False)

    def test_extra_specs_matches_with_op_seq(self):
        self._do_extra_specs_ops_test(
            value='123',
            req='s== 123',
            matches=True)

    def test_extra_specs_fails_with_op_seq(self):
        self._do_extra_specs_ops_test(
            value='1234',
            req='s== 123',
            matches=False)

    def test_extra_specs_matches_with_op_sneq(self):
        self._do_extra_specs_ops_test(
            value='1234',
            req='s!= 123',
            matches=True)

    def test_extra_specs_fails_with_op_sneq(self):
        self._do_extra_specs_ops_test(
            value='123',
            req='s!= 123',
            matches=False)

    def test_extra_specs_fails_with_op_sge(self):
        self._do_extra_specs_ops_test(
            value='1000',
            req='s>= 234',
            matches=False)

    def test_extra_specs_fails_with_op_sle(self):
        self._do_extra_specs_ops_test(
            value='1234',
            req='s<= 1000',
            matches=False)

    def test_extra_specs_fails_with_op_sl(self):
        self._do_extra_specs_ops_test(
            value='2',
            req='s< 12',
            matches=False)

    def test_extra_specs_fails_with_op_sg(self):
        self._do_extra_specs_ops_test(
            value='12',
            req='s> 2',
            matches=False)

    def test_extra_specs_matches_with_op_in(self):
        self._do_extra_specs_ops_test(
            value='12311321',
            req='<in> 11',
            matches=True)

    def test_extra_specs_matches_with_op_in2(self):
        self._do_extra_specs_ops_test(
            value='12311321',
            req='<in> 12311321',
            matches=True)

    def test_extra_specs_matches_with_op_in3(self):
        self._do_extra_specs_ops_test(
            value='12311321',
            req='<in> 12311321 <in>',
            matches=True)

    def test_extra_specs_fails_with_op_in(self):
        self._do_extra_specs_ops_test(
            value='12310321',
            req='<in> 11',
            matches=False)

    def test_extra_specs_fails_with_op_in2(self):
        self._do_extra_specs_ops_test(
            value='12310321',
            req='<in> 11 <in>',
            matches=False)

    def test_extra_specs_matches_with_op_is(self):
        self._do_extra_specs_ops_test(
            value=True,
            req='<is> True',
            matches=True)

    def test_extra_specs_matches_with_op_is2(self):
        self._do_extra_specs_ops_test(
            value=False,
            req='<is> False',
            matches=True)

    def test_extra_specs_matches_with_op_is3(self):
        self._do_extra_specs_ops_test(
            value=False,
            req='<is> Nonsense',
            matches=True)

    def test_extra_specs_fails_with_op_is(self):
        self._do_extra_specs_ops_test(
            value=True,
            req='<is> False',
            matches=False)

    def test_extra_specs_fails_with_op_is2(self):
        self._do_extra_specs_ops_test(
            value=False,
            req='<is> True',
            matches=False)

    def test_extra_specs_matches_with_op_or(self):
        self._do_extra_specs_ops_test(
            value='12',
            req='<or> 11 <or> 12',
            matches=True)

    def test_extra_specs_matches_with_op_or2(self):
        self._do_extra_specs_ops_test(
            value='12',
            req='<or> 11 <or> 12 <or>',
            matches=True)

    def test_extra_specs_fails_with_op_or(self):
        self._do_extra_specs_ops_test(
            value='13',
            req='<or> 11 <or> 12',
            matches=False)

    def test_extra_specs_fails_with_op_or2(self):
        self._do_extra_specs_ops_test(
            value='13',
            req='<or> 11 <or> 12 <or>',
            matches=False)

    def test_extra_specs_matches_with_op_le(self):
        self._do_extra_specs_ops_test(
            value='2',
            req='<= 10',
            matches=True)

    def test_extra_specs_fails_with_op_le(self):
        self._do_extra_specs_ops_test(
            value='3',
            req='<= 2',
            matches=False)

    def test_extra_specs_matches_with_op_ge(self):
        self._do_extra_specs_ops_test(
            value='3',
            req='>= 1',
            matches=True)

    def test_extra_specs_fails_with_op_ge(self):
        self._do_extra_specs_ops_test(
            value='2',
            req='>= 3',
            matches=False)

    def test_extra_specs_fails_none_req(self):
        self._do_extra_specs_ops_test(
            value='foo',
            req=None,
            matches=False)

    def test_extra_specs_matches_none_req(self):
        self._do_extra_specs_ops_test(
            value=None,
            req=None,
            matches=True)


@ddt.ddt
class BasicFiltersTestCase(NodeFiltersTestCase):
    """Test case for node filters."""

    def setUp(self):
        super(BasicFiltersTestCase, self).setUp()
        self.json_query = jsonutils.dumps(
            ['and', ['>=', '$free_ram_mb', 1024],
             ['>=', '$free_disk_mb', 200 * 1024]])

    def test_all_filters(self):
        # Double check at least a couple of known filters exist
        self.assertIn('JsonFilter', self.class_map)
        self.assertIn('CapabilitiesFilter', self.class_map)
        self.assertIn('AvailabilityZoneFilter', self.class_map)
#        self.assertIn('IgnoreAttemptedNodesFilter', self.class_map)

    def _do_test_type_filter_extra_specs(self, ecaps, especs, passes):
        filt_cls = self.class_map['CapabilitiesFilter']()
        capabilities = {'enabled': True}
        capabilities.update(ecaps)
        service = {'disabled': False}
        filter_properties = {'resource_type': {'name': 'fake_type',
                                               'extra_specs': especs}}
        node = fakes.FakeNodeState('node1',
                                   {'free_capacity_gb': 1024,
                                    'capabilities': capabilities,
                                    'service': service})
        assertion = self.assertTrue if passes else self.assertFalse
        assertion(filt_cls.node_passes(node, filter_properties))

    def test_capability_filter_passes_extra_specs_simple(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': '1', 'opt2': '2'},
            especs={'opt1': '1', 'opt2': '2'},
            passes=True)

    def test_capability_filter_fails_extra_specs_simple(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': '1', 'opt2': '2'},
            especs={'opt1': '1', 'opt2': '222'},
            passes=False)

    def test_capability_filter_passes_extra_specs_complex(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': 10, 'opt2': 5},
            especs={'opt1': '>= 2', 'opt2': '<= 8'},
            passes=True)

    def test_capability_filter_fails_extra_specs_complex(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': 10, 'opt2': 5},
            especs={'opt1': '>= 2', 'opt2': '>= 8'},
            passes=False)

    def test_capability_filter_passes_extra_specs_list_simple(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': ['1', '2'], 'opt2': '2'},
            especs={'opt1': '1', 'opt2': '2'},
            passes=True)

    @ddt.data('<is> True', '<is> False')
    def test_capability_filter_passes_extra_specs_list_complex(self, opt1):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': [True, False], 'opt2': ['1', '2']},
            especs={'opt1': opt1, 'opt2': '<= 8'},
            passes=True)

    def test_capability_filter_fails_extra_specs_list_simple(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': ['1', '2'], 'opt2': ['2']},
            especs={'opt1': '3', 'opt2': '2'},
            passes=False)

    def test_capability_filter_fails_extra_specs_list_complex(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'opt1': [True, False], 'opt2': ['1', '2']},
            especs={'opt1': 'fake', 'opt2': '<= 8'},
            passes=False)

    def test_capability_filter_passes_scope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv1': {'opt1': 10}},
            especs={'capabilities:scope_lv1:opt1': '>= 2'},
            passes=True)

    def test_capability_filter_passes_fakescope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv1': {'opt1': 10}, 'opt2': 5},
            especs={'scope_lv1:opt1': '= 2', 'opt2': '>= 3'},
            passes=True)

    def test_capability_filter_fails_scope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv1': {'opt1': 10}},
            especs={'capabilities:scope_lv1:opt1': '<= 2'},
            passes=False)

    def test_capability_filter_passes_multi_level_scope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'scope_lv1':
                                 {'scope_lv2': {'opt1': 10}}}},
            especs={'capabilities:scope_lv0:scope_lv1:scope_lv2:opt1': '>= 2'},
            passes=True)

    def test_capability_filter_fails_unenough_level_scope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'scope_lv1': None}},
            especs={'capabilities:scope_lv0:scope_lv1:scope_lv2:opt1': '>= 2'},
            passes=False)

    def test_capability_filter_fails_wrong_scope_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'opt1': 10}},
            especs={'capabilities:scope_lv1:opt1': '>= 2'},
            passes=False)

    def test_capability_filter_passes_none_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'opt1': None}},
            especs={'capabilities:scope_lv0:opt1': None},
            passes=True)

    def test_capability_filter_fails_none_extra_specs(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'opt1': 10}},
            especs={'capabilities:scope_lv0:opt1': None},
            passes=False)

    def test_capability_filter_fails_none_caps(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'opt1': None}},
            especs={'capabilities:scope_lv0:opt1': 'foo'},
            passes=False)

    def test_capability_filter_passes_multi_level_scope_extra_specs_list(self):
        self._do_test_type_filter_extra_specs(
            ecaps={
                'scope_lv0': {
                    'scope_lv1': {
                        'scope_lv2': {
                            'opt1': [True, False],
                        },
                    },
                },
            },
            especs={
                'capabilities:scope_lv0:scope_lv1:scope_lv2:opt1': '<is> True',
            },
            passes=True)

    def test_capability_filter_fails_multi_level_scope_extra_specs_list(self):
        self._do_test_type_filter_extra_specs(
            ecaps={
                'scope_lv0': {
                    'scope_lv1': {
                        'scope_lv2': {
                            'opt1': [True, False],
                            'opt2': ['1', '2'],
                        },
                    },
                },
            },
            especs={
                'capabilities:scope_lv0:scope_lv1:scope_lv2:opt1': '<is> True',
                'capabilities:scope_lv0:scope_lv1:scope_lv2:opt2': '3',
            },
            passes=False)

    def test_capability_filter_fails_wrong_scope_extra_specs_list(self):
        self._do_test_type_filter_extra_specs(
            ecaps={'scope_lv0': {'opt1': [True, False]}},
            especs={'capabilities:scope_lv1:opt1': '<is> True'},
            passes=False)

    def test_json_filter_passes(self):
        filt_cls = self.class_map['JsonFilter']()
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'root_gb': 200,
                                               'ephemeral_gb': 0},
                             'scheduler_hints': {'query': self.json_query}}
        capabilities = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 1024,
                                    'free_disk_mb': 200 * 1024,
                                    'capabilities': capabilities})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_passes_with_no_query(self):
        filt_cls = self.class_map['JsonFilter']()
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'root_gb': 200,
                                               'ephemeral_gb': 0}}
        capabilities = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 0,
                                    'free_disk_mb': 0,
                                    'capabilities': capabilities})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_fails_on_memory(self):
        filt_cls = self.class_map['JsonFilter']()
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'root_gb': 200,
                                               'ephemeral_gb': 0},
                             'scheduler_hints': {'query': self.json_query}}
        capabilities = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 1023,
                                    'free_disk_mb': 200 * 1024,
                                    'capabilities': capabilities})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_fails_on_disk(self):
        filt_cls = self.class_map['JsonFilter']()
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'root_gb': 200,
                                               'ephemeral_gb': 0},
                             'scheduler_hints': {'query': self.json_query}}
        capabilities = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 1024,
                                    'free_disk_mb': (200 * 1024) - 1,
                                    'capabilities': capabilities})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_fails_on_caps_disabled(self):
        filt_cls = self.class_map['JsonFilter']()
        json_query = jsonutils.dumps(
            ['and', ['>=', '$free_ram_mb', 1024],
             ['>=', '$free_disk_mb', 200 * 1024],
             '$capabilities.enabled'])
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'root_gb': 200,
                                               'ephemeral_gb': 0},
                             'scheduler_hints': {'query': json_query}}
        capabilities = {'enabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 1024,
                                    'free_disk_mb': 200 * 1024,
                                    'capabilities': capabilities})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_fails_on_service_disabled(self):
        filt_cls = self.class_map['JsonFilter']()
        json_query = jsonutils.dumps(
            ['and', ['>=', '$free_ram_mb', 1024],
             ['>=', '$free_disk_mb', 200 * 1024],
             ['not', '$service.disabled']])
        filter_properties = {'resource_type': {'memory_mb': 1024,
                                               'local_gb': 200},
                             'scheduler_hints': {'query': json_query}}
        capabilities = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 1024,
                                    'free_disk_mb': 200 * 1024,
                                    'capabilities': capabilities})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_happy_day(self):
        """Test json filter more thoroughly."""
        filt_cls = self.class_map['JsonFilter']()
        raw = ['and',
               '$capabilities.enabled',
               ['=', '$capabilities.opt1', 'match'],
               ['or',
                ['and',
                 ['<', '$free_ram_mb', 30],
                 ['<', '$free_disk_mb', 300]],
                ['and',
                 ['>', '$free_ram_mb', 30],
                 ['>', '$free_disk_mb', 300]]]]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }

        # Passes
        capabilities = {'enabled': True, 'opt1': 'match'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 10,
                                    'free_disk_mb': 200,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

        # Passes
        capabilities = {'enabled': True, 'opt1': 'match'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 40,
                                    'free_disk_mb': 400,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

        # Fails due to capabilities being disabled
        capabilities = {'enabled': False, 'opt1': 'match'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 40,
                                    'free_disk_mb': 400,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

        # Fails due to being exact memory/disk we don't want
        capabilities = {'enabled': True, 'opt1': 'match'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 30,
                                    'free_disk_mb': 300,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

        # Fails due to memory lower but disk higher
        capabilities = {'enabled': True, 'opt1': 'match'}
        service = {'disabled': False}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 20,
                                    'free_disk_mb': 400,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

        # Fails due to capabilities 'opt1' not equal
        capabilities = {'enabled': True, 'opt1': 'no-match'}
        service = {'enabled': True}
        node = fakes.FakeNodeState('node1',
                                   {'free_ram_mb': 20,
                                    'free_disk_mb': 400,
                                    'capabilities': capabilities,
                                    'service': service})
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_basic_operators(self):
        filt_cls = self.class_map['JsonFilter']()
        node = fakes.FakeNodeState('node1',
                                   {'capabilities': {'enabled': True}})
        # (operator, arguments, expected_result)
        ops_to_test = [
            ['=', [1, 1], True],
            ['=', [1, 2], False],
            ['<', [1, 2], True],
            ['<', [1, 1], False],
            ['<', [2, 1], False],
            ['>', [2, 1], True],
            ['>', [2, 2], False],
            ['>', [2, 3], False],
            ['<=', [1, 2], True],
            ['<=', [1, 1], True],
            ['<=', [2, 1], False],
            ['>=', [2, 1], True],
            ['>=', [2, 2], True],
            ['>=', [2, 3], False],
            ['in', [1, 1], True],
            ['in', [1, 1, 2, 3], True],
            ['in', [4, 1, 2, 3], False],
            ['not', [True], False],
            ['not', [False], True],
            ['or', [True, False], True],
            ['or', [False, False], False],
            ['and', [True, True], True],
            ['and', [False, False], False],
            ['and', [True, False], False],
            # Nested ((True or False) and (2 > 1)) == Passes
            ['and', [['or', True, False], ['>', 2, 1]], True]]

        for (op, args, expected) in ops_to_test:
            raw = [op] + args
            filter_properties = {
                'scheduler_hints': {
                    'query': jsonutils.dumps(raw),
                },
            }
            self.assertEqual(expected,
                             filt_cls.node_passes(node, filter_properties))

        # This results in [False, True, False, True] and if any are True
        # then it passes...
        raw = ['not', True, False, True, False]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

        # This results in [False, False, False] and if any are True
        # then it passes...which this doesn't
        raw = ['not', True, True, True]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_unknown_operator_raises(self):
        filt_cls = self.class_map['JsonFilter']()
        raw = ['!=', 1, 2]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        node = fakes.FakeNodeState('node1',
                                   {'capabilities': {'enabled': True}})
        self.assertRaises(KeyError,
                          filt_cls.node_passes, node, filter_properties)

    def test_json_filter_empty_filters_pass(self):
        filt_cls = self.class_map['JsonFilter']()
        node = fakes.FakeNodeState('node1',
                                   {'capabilities': {'enabled': True}})

        raw = []
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertTrue(filt_cls.node_passes(node, filter_properties))
        raw = {}
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_invalid_num_arguments_fails(self):
        filt_cls = self.class_map['JsonFilter']()
        node = fakes.FakeNodeState('node1',
                                   {'capabilities': {'enabled': True}})

        raw = ['>', ['and', ['or', ['not', ['<', ['>=', ['<=', ['in', ]]]]]]]]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

        raw = ['>', 1]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertFalse(filt_cls.node_passes(node, filter_properties))

    def test_json_filter_unknown_variable_ignored(self):
        filt_cls = self.class_map['JsonFilter']()
        node = fakes.FakeNodeState('node1',
                                   {'capabilities': {'enabled': True}})

        raw = ['=', '$........', 1, 1]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

        raw = ['=', '$foo', 2, 2]
        filter_properties = {
            'scheduler_hints': {
                'query': jsonutils.dumps(raw),
            },
        }
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    @staticmethod
    def _make_zone_request(zone, is_admin=False):
        ctxt = context.RequestContext('fake', 'fake', is_admin=is_admin)
        return {
            'context': ctxt,
            'request_spec': {
                'instance_properties': {
                    'availability_zone': zone
                }
            }
        }

    def test_availability_zone_filter_same(self):
        filt_cls = self.class_map['AvailabilityZoneFilter']()
        service = {'availability_zone': 'nova'}
        request = self._make_zone_request('nova')
        node = fakes.FakeNodeState('node1',
                                   {'service': service})
        self.assertTrue(filt_cls.node_passes(node, request))

    def test_availability_zone_filter_different(self):
        filt_cls = self.class_map['AvailabilityZoneFilter']()
        service = {'availability_zone': 'nova'}
        request = self._make_zone_request('bad')
        node = fakes.FakeNodeState('node1',
                                   {'service': service})
        self.assertFalse(filt_cls.node_passes(node, request))

    def test_availability_zone_filter_empty(self):
        filt_cls = self.class_map['AvailabilityZoneFilter']()
        service = {'availability_zone': 'nova'}
        request = {}
        node = fakes.FakeNodeState('node1',
                                   {'service': service})
        self.assertTrue(filt_cls.node_passes(node, request))

    def test_ignore_attempted_nodes_filter_disabled(self):
        # Test case where re-scheduling is disabled.
        filt_cls = self.class_map['IgnoreAttemptedNodesFilter']()
        node = fakes.FakeNodeState('node1', {})
        filter_properties = {}
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    def test_ignore_attempted_nodes_filter_pass(self):
        # Node not previously tried.
        filt_cls = self.class_map['IgnoreAttemptedNodesFilter']()
        node = fakes.FakeNodeState('node1', {})
        attempted = dict(num_attempts=2, nodes=['node2'])
        filter_properties = dict(retry=attempted)
        self.assertTrue(filt_cls.node_passes(node, filter_properties))

    def test_ignore_attempted_nodes_filter_fail(self):
        # Node was already tried.
        filt_cls = self.class_map['IgnoreAttemptedNodesFilter']()
        node = fakes.FakeNodeState('node1', {})
        attempted = dict(num_attempts=2, nodes=['node1'])
        filter_properties = dict(retry=attempted)
        self.assertFalse(filt_cls.node_passes(node, filter_properties))
