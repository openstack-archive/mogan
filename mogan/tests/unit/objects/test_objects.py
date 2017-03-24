#    Copyright 2013 IBM Corp.
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

import datetime
import gettext
import iso8601

import mock
from oslo_context import context
from oslo_versionedobjects import base as object_base
from oslo_versionedobjects import exception as object_exception
from oslo_versionedobjects import fixture as object_fixture
import six

from mogan.objects import base
from mogan.objects import fields
from mogan.tests import base as test_base

gettext.install('mogan')


@base.MoganObjectRegistry.register
class MyObj(base.MoganObject, object_base.VersionedObjectDictCompat):
    VERSION = '1.1'

    fields = {'foo': fields.IntegerField(),
              'bar': fields.StringField(),
              'missing': fields.StringField(),
              }

    def obj_load_attr(self, attrname):
        setattr(self, attrname, 'loaded!')

    @object_base.remotable_classmethod
    def query(cls, context):
        obj = cls(context)
        obj.foo = 1
        obj.bar = 'bar'
        obj.obj_reset_changes()
        return obj

    @object_base.remotable
    def marco(self, context=None):
        return 'polo'

    @object_base.remotable
    def update_test(self, ctxt=None):
        if ctxt and ctxt.tenant == 'alternate':
            self.bar = 'alternate-context'
        else:
            self.bar = 'updated'

    @object_base.remotable
    def save(self, context=None):
        self.obj_reset_changes()

    @object_base.remotable
    def refresh(self, context=None):
        self.foo = 321
        self.bar = 'refreshed'
        self.obj_reset_changes()

    @object_base.remotable
    def modify_save_modify(self, context=None):
        self.bar = 'meow'
        self.save()
        self.foo = 42


class MyObj2(object):
    @classmethod
    def obj_name(cls):
        return 'MyObj'

    @object_base.remotable_classmethod
    def get(cls, *args, **kwargs):
        pass


@base.MoganObjectRegistry.register_if(False)
class TestSubclassedObject(MyObj):
    fields = {'new_field': fields.StringField()}


class _TestObject(object):
    def test_hydration_type_error(self):
        primitive = {'mogan_object.name': 'MyObj',
                     'mogan_object.namespace': 'mogan',
                     'mogan_object.version': '1.5',
                     'mogan_object.data': {'foo': 'a'}}
        self.assertRaises(ValueError, MyObj.obj_from_primitive, primitive)

    def test_hydration(self):
        primitive = {'mogan_object.name': 'MyObj',
                     'mogan_object.namespace': 'mogan',
                     'mogan_object.version': '1.5',
                     'mogan_object.data': {'foo': 1}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(1, obj.foo)

    def test_hydration_bad_ns(self):
        primitive = {'mogan_object.name': 'MyObj',
                     'mogan_object.namespace': 'foo',
                     'mogan_object.version': '1.5',
                     'mogan_object.data': {'foo': 1}}
        self.assertRaises(object_exception.UnsupportedObjectError,
                          MyObj.obj_from_primitive, primitive)

    def test_dehydration(self):
        expected = {'mogan_object.name': 'MyObj',
                    'mogan_object.namespace': 'mogan',
                    'mogan_object.version': '1.5',
                    'mogan_object.data': {'foo': 1}}
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_get_updates(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_object_property(self):
        obj = MyObj(self.context, foo=1)
        self.assertEqual(1, obj.foo)

    def test_object_property_type_error(self):
        obj = MyObj(self.context)

        def fail():
            obj.foo = 'a'
        self.assertRaises(ValueError, fail)

    def test_load(self):
        obj = MyObj(self.context)
        self.assertEqual('loaded!', obj.bar)

    def test_load_in_base(self):
        @base.MoganObjectRegistry.register_if(False)
        class Foo(base.MoganObject, object_base.VersionedObjectDictCompat):
            fields = {'foobar': fields.IntegerField()}
        obj = Foo(self.context)

        self.assertRaisesRegex(
            NotImplementedError, "Cannot load 'foobar' in the base class",
            getattr, obj, 'foobar')

    def test_loaded_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual('loaded!', obj.bar)
        expected = {'mogan_object.name': 'MyObj',
                    'mogan_object.namespace': 'mogan',
                    'mogan_object.version': '1.5',
                    'mogan_object.changes': ['bar'],
                    'mogan_object.data': {'foo': 1,
                                          'bar': 'loaded!'}}
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_changes_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        primitive = obj.obj_to_primitive()
        self.assertIn('mogan_object.changes', primitive)
        obj2 = MyObj.obj_from_primitive(primitive)
        self.assertEqual(set(['foo']), obj2.obj_what_changed())
        obj2.obj_reset_changes()
        self.assertEqual(set(), obj2.obj_what_changed())

    def test_unknown_objtype(self):
        self.assertRaises(object_exception.UnsupportedObjectError,
                          base.MoganObject.obj_class_from_name, 'foo', '1.0')

    def test_with_alternate_context(self):
        ctxt1 = context.RequestContext('foo', 'foo')
        ctxt2 = context.RequestContext('bar', tenant='alternate')
        obj = MyObj.query(ctxt1)
        obj.update_test(ctxt2)
        self.assertEqual('alternate-context', obj.bar)

    def test_orphaned_object(self):
        obj = MyObj.query(self.context)
        obj._context = None
        self.assertRaises(object_exception.OrphanedObjectError,
                          obj.update_test)

    def test_changed_1(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.update_test(self.context)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_2(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.save()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_3(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.refresh()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(321, obj.foo)
        self.assertEqual('refreshed', obj.bar)

    def test_changed_4(self):
        obj = MyObj.query(self.context)
        obj.bar = 'something'
        self.assertEqual(set(['bar']), obj.obj_what_changed())
        obj.modify_save_modify(self.context)
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        self.assertEqual(42, obj.foo)
        self.assertEqual('meow', obj.bar)

    def test_static_result(self):
        obj = MyObj.query(self.context)
        self.assertEqual('bar', obj.bar)
        result = obj.marco()
        self.assertEqual('polo', result)

    def test_updates(self):
        obj = MyObj.query(self.context)
        self.assertEqual(1, obj.foo)
        obj.update_test()
        self.assertEqual('updated', obj.bar)

    def test_base_attributes(self):
        dt = datetime.datetime(1955, 11, 5, 0, 0, tzinfo=iso8601.iso8601.Utc())
        datatime = fields.DateTimeField()
        obj = MyObj(self.context)
        obj.created_at = dt
        obj.updated_at = dt
        expected = {'mogan_object.name': 'MyObj',
                    'mogan_object.namespace': 'mogan',
                    'mogan_object.version': '1.5',
                    'mogan_object.changes':
                        ['created_at', 'updated_at'],
                    'mogan_object.data':
                        {'created_at': datatime.stringify(dt),
                         'updated_at': datatime.stringify(dt),
                         }
                    }
        actual = obj.obj_to_primitive()
        # mogan_object.changes is built from a set and order is undefined
        self.assertEqual(sorted(expected['mogan_object.changes']),
                         sorted(actual['mogan_object.changes']))
        del expected['mogan_object.changes'], actual['mogan_object.changes']
        self.assertEqual(expected, actual)

    def test_contains(self):
        obj = MyObj(self.context)
        self.assertNotIn('foo', obj)
        obj.foo = 1
        self.assertIn('foo', obj)
        self.assertNotIn('does_not_exist', obj)

    def test_obj_attr_is_set(self):
        obj = MyObj(self.context, foo=1)
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertFalse(obj.obj_attr_is_set('bar'))
        self.assertRaises(AttributeError, obj.obj_attr_is_set, 'bang')

    def test_get(self):
        obj = MyObj(self.context, foo=1)
        # Foo has value, should not get the default
        self.assertEqual(1, obj.get('foo', 2))
        # Foo has value, should return the value without error
        self.assertEqual(1, obj.get('foo'))
        # Bar is not loaded, so we should get the default
        self.assertEqual('not-loaded', obj.get('bar', 'not-loaded'))
        # Bar without a default should lazy-load
        self.assertEqual('loaded!', obj.get('bar'))
        # Bar now has a default, but loaded value should be returned
        self.assertEqual('loaded!', obj.get('bar', 'not-loaded'))
        # Invalid attribute should raise AttributeError
        self.assertRaises(AttributeError, obj.get, 'nothing')
        # ...even with a default
        self.assertRaises(AttributeError, obj.get, 'nothing', 3)

    def test_object_inheritance(self):
        base_fields = list(base.MoganObject.fields)
        myobj_fields = ['foo', 'bar', 'missing'] + base_fields
        myobj3_fields = ['new_field']
        self.assertTrue(issubclass(TestSubclassedObject, MyObj))
        self.assertEqual(len(myobj_fields), len(MyObj.fields))
        self.assertEqual(set(myobj_fields), set(MyObj.fields.keys()))
        self.assertEqual(len(myobj_fields) + len(myobj3_fields),
                         len(TestSubclassedObject.fields))
        self.assertEqual(set(myobj_fields) | set(myobj3_fields),
                         set(TestSubclassedObject.fields.keys()))

    def test_get_changes(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_obj_fields(self):
        @base.MoganObjectRegistry.register_if(False)
        class TestObj(base.MoganObject,
                      object_base.VersionedObjectDictCompat):
            fields = {'foo': fields.IntegerField()}
            obj_extra_fields = ['bar']

            @property
            def bar(self):
                return 'this is bar'

        obj = TestObj(self.context)
        self.assertEqual(set(['created_at', 'updated_at', 'foo', 'bar']),
                         set(obj.obj_fields))

    def test_refresh_object(self):
        @base.MoganObjectRegistry.register_if(False)
        class TestObj(base.MoganObject,
                      object_base.VersionedObjectDictCompat):
            fields = {'foo': fields.IntegerField(),
                      'bar': fields.StringField()}

        obj = TestObj(self.context)
        current_obj = TestObj(self.context)
        obj.foo = 10
        obj.bar = 'obj.bar'
        current_obj.foo = 2
        current_obj.bar = 'current.bar'
        obj.obj_refresh(current_obj)
        self.assertEqual(2, obj.foo)
        self.assertEqual('current.bar', obj.bar)

    def test_obj_constructor(self):
        obj = MyObj(self.context, foo=123, bar='abc')
        self.assertEqual(123, obj.foo)
        self.assertEqual('abc', obj.bar)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())

    def test_assign_value_without_DictCompat(self):
        class TestObj(base.MoganObject):
            fields = {'foo': fields.IntegerField(),
                      'bar': fields.StringField()}
        obj = TestObj(self.context)
        obj.foo = 10
        err_message = ''
        try:
            obj['bar'] = 'value'
        except TypeError as e:
            err_message = six.text_type(e)
        finally:
            self.assertIn("'TestObj' object does not support item assignment",
                          err_message)


# The hashes are help developers to check if the change of objects need a
# version bump. It is md5 hash of object fields and remotable methods.
# The fingerprint values should only be changed if there is a version bump.
expected_object_fingerprints = {
    'Instance': '1.0-a4d843f506946e824fe6accb842e0a84',
    'ComputeNode': '1.0-36221253681d9acb88efe2a9113071c7',
    'ComputeNodeList': '1.0-33a2e1bb91ad4082f9f63429b77c1244',
    'ComputePort': '1.0-ca4c1817ad7324286813f2cfcdcf802e',
    'ComputePortList': '1.0-33a2e1bb91ad4082f9f63429b77c1244',
    'InstanceFault': '1.0-6b5b01b2cc7b6b547837acb168ec6eb9',
    'InstanceFaultList': '1.0-43e8aad0258652921f929934e9e048fd',
    'InstanceType': '1.0-589b096651fcdb30898ff50f748dd948',
    'MyObj': '1.1-aad62eedc5a5cc8bcaf2982c285e753f',
    'InstanceNic': '1.0-78744332fe105f9c1796dc5295713d9f',
    'InstanceNics': '1.0-33a2e1bb91ad4082f9f63429b77c1244',
    'Quota': '1.0-c8caa082f4d726cb63fdc5943f7cd186',
}


class TestObjectVersions(test_base.TestCase):

    def test_object_version_check(self):
        classes = base.MoganObjectRegistry.obj_classes()
        # We will test the notification objects specifically, here
        # we only test the versioned objects.
        for noti_cls in base.MoganObjectRegistry.notification_classes:
            classes.pop(noti_cls.__name__, None)
        checker = object_fixture.ObjectVersionChecker(obj_classes=classes)
        # Compute the difference between actual fingerprints and
        # expect fingerprints. expect = actual = {} if there is no change.
        expect, actual = checker.test_hashes(expected_object_fingerprints)
        self.assertEqual(expect, actual,
                         "Some objects fields or remotable methods have been "
                         "modified. Please make sure the version of those "
                         "objects have been bumped and then update "
                         "expected_object_fingerprints with the new hashes. ")


class TestObjectSerializer(test_base.TestCase):

    def test_object_serialization(self):
        ser = base.MoganObjectSerializer()
        obj = MyObj(self.context)
        primitive = ser.serialize_entity(self.context, obj)
        self.assertIn('mogan_object.name', primitive)
        obj2 = ser.deserialize_entity(self.context, primitive)
        self.assertIsInstance(obj2, MyObj)
        self.assertEqual(self.context, obj2._context)

    def test_object_serialization_iterables(self):
        ser = base.MoganObjectSerializer()
        obj = MyObj(self.context)
        for iterable in (list, tuple, set):
            thing = iterable([obj])
            primitive = ser.serialize_entity(self.context, thing)
            self.assertEqual(1, len(primitive))
            for item in primitive:
                self.assertNotIsInstance(item, base.MoganObject)
            thing2 = ser.deserialize_entity(self.context, primitive)
            self.assertEqual(1, len(thing2))
            for item in thing2:
                self.assertIsInstance(item, MyObj)


class TestRegistry(test_base.TestCase):
    @mock.patch('mogan.objects.base.objects')
    def test_hook_chooses_newer_properly(self, mock_objects):
        reg = base.MoganObjectRegistry()
        reg.registration_hook(MyObj, 0)

        class MyNewerObj(object):
            VERSION = '1.123'

            @classmethod
            def obj_name(cls):
                return 'MyObj'

        self.assertEqual(MyObj, mock_objects.MyObj)
        reg.registration_hook(MyNewerObj, 0)
        self.assertEqual(MyNewerObj, mock_objects.MyObj)
