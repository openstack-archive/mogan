# Copyright 2016 Huawei Technologies Co.,LTD.
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

from oslo_versionedobjects import fields as object_fields

from nimble.objects import fields
from nimble.tests import base as test_base


class FakeFieldType(object_fields.FieldType):
    def coerce(self, obj, attr, value):
        return '*%s*' % value

    def to_primitive(self, obj, attr, value):
        return '!%s!' % value

    def from_primitive(self, obj, attr, value):
        return value[1:-1]


class FakeEnum(object_fields.Enum):
    FROG = "frog"
    PLATYPUS = "platypus"
    ALLIGATOR = "alligator"

    ALL = (FROG, PLATYPUS, ALLIGATOR)

    def __init__(self, **kwargs):
        super(FakeEnum, self).__init__(valid_values=FakeEnum.ALL,
                                       **kwargs)


class FakeEnumAlt(object_fields.Enum):
    FROG = "frog"
    PLATYPUS = "platypus"
    AARDVARK = "aardvark"

    ALL = (FROG, PLATYPUS, AARDVARK)

    def __init__(self, **kwargs):
        super(FakeEnumAlt, self).__init__(valid_values=FakeEnumAlt.ALL,
                                          **kwargs)


class FakeEnumField(object_fields.BaseEnumField):
    AUTO_TYPE = FakeEnum()


class FakeEnumAltField(object_fields.BaseEnumField):
    AUTO_TYPE = FakeEnumAlt()


class TestField(test_base.BaseTestCase):
    def setUp(self):
        super(TestField, self).setUp()
        self.field = fields.Field(FakeFieldType())
        self.coerce_good_values = [('foo', '*foo*')]
        self.coerce_bad_values = []
        self.to_primitive_values = [('foo', '!foo!')]
        self.from_primitive_values = [('!foo!', 'foo')]

    def test_coerce_good_values(self):
        for in_val, out_val in self.coerce_good_values:
            self.assertEqual(out_val, self.field.coerce('obj', 'attr', in_val))

    def test_coerce_bad_values(self):
        for in_val in self.coerce_bad_values:
            self.assertRaises((TypeError, ValueError),
                              self.field.coerce, 'obj', 'attr', in_val)

    def test_to_primitive(self):
        for in_val, prim_val in self.to_primitive_values:
            self.assertEqual(prim_val, self.field.to_primitive('obj', 'attr',
                                                               in_val))

    def test_from_primitive(self):
        class ObjectLikeThing(object):
            _context = 'context'

        for prim_val, out_val in self.from_primitive_values:
            self.assertEqual(out_val, self.field.from_primitive(
                ObjectLikeThing, 'attr', prim_val))

    def test_stringify(self):
        self.assertEqual('123', self.field.stringify(123))


class TestNotificationPriority(TestField):
    def setUp(self):
        super(TestNotificationPriority, self).setUp()
        self.field = fields.NotificationPriorityField()
        self.coerce_good_values = [('audit', 'audit'),
                                   ('critical', 'critical'),
                                   ('debug', 'debug'),
                                   ('error', 'error'),
                                   ('sample', 'sample'),
                                   ('warn', 'warn')]
        self.coerce_bad_values = ['warning']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'warn'", self.field.stringify('warn'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'warning')


class TestNotificationPhase(TestField):
    def setUp(self):
        super(TestNotificationPhase, self).setUp()
        self.field = fields.NotificationPhaseField()
        self.coerce_good_values = [('start', 'start'),
                                   ('end', 'end'),
                                   ('error', 'error')]
        self.coerce_bad_values = ['begin']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'error'", self.field.stringify('error'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'begin')


class TestNotificationAction(TestField):
    def setUp(self):
        super(TestNotificationAction, self).setUp()
        self.field = fields.NotificationActionField()
        self.coerce_good_values = [('update', 'update')]
        self.coerce_bad_values = ['magic']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'update'", self.field.stringify('update'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'magic')
