# Copyright 2017 Fiberhome Integration Technologies Co.,LTD.
# All Rights Reserved.
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

"""Tests for manipulating Server tags via the DB API"""

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbServerTagTestCase(base.DbTestCase):

    def setUp(self):
        super(DbServerTagTestCase, self).setUp()
        self.server = utils.create_test_server()

    def test_set_server_tags(self):
        tags = self.dbapi.set_server_tags(self.context, self.server.id,
                                          ['tag1', 'tag2'])
        self.assertEqual(self.server.id, tags[0].server_id)
        self.assertItemsEqual(['tag1', 'tag2'], [tag.tag for tag in tags])

        tags = self.dbapi.set_server_tags(self.context, self.server.id, [])
        self.assertEqual([], tags)

    def test_set_server_tags_duplicate(self):
        tags = self.dbapi.set_server_tags(self.context, self.server.id,
                                          ['tag1', 'tag2', 'tag2'])
        self.assertEqual(self.server.id, tags[0].server_id)
        self.assertItemsEqual(['tag1', 'tag2'], [tag.tag for tag in tags])

    def test_set_server_tags_server_not_exist(self):
        self.assertRaises(exception.ServerNotFound,
                          self.dbapi.set_server_tags,
                          self.context, '1234', ['tag1', 'tag2'])

    def test_get_server_tags_by_server_id(self):
        self.dbapi.set_server_tags(self.context, self.server.id,
                                   ['tag1', 'tag2'])
        tags = self.dbapi.get_server_tags_by_server_id(self.context,
                                                       self.server.id)
        self.assertEqual(self.server.id, tags[0].server_id)
        self.assertItemsEqual(['tag1', 'tag2'], [tag.tag for tag in tags])

    def test_get_server_tags_empty(self):
        tags = self.dbapi.get_server_tags_by_server_id(self.context,
                                                       self.server.id)
        self.assertEqual([], tags)

    def test_get_server_tags_server_not_exist(self):
        self.assertRaises(exception.ServerNotFound,
                          self.dbapi.get_server_tags_by_server_id,
                          self.context, '123')

    def test_unset_server_tags(self):
        self.dbapi.set_server_tags(self.context, self.server.id,
                                   ['tag1', 'tag2'])
        self.dbapi.unset_server_tags(self.context, self.server.id)
        tags = self.dbapi.get_server_tags_by_server_id(self.context,
                                                       self.server.id)
        self.assertEqual([], tags)

    def test_unset_empty_server_tags(self):
        self.dbapi.unset_server_tags(self.context, self.server.id)
        tags = self.dbapi.get_server_tags_by_server_id(self.context,
                                                       self.server.id)
        self.assertEqual([], tags)

    def test_unset_server_tags_server_not_exist(self):
        self.assertRaises(exception.ServerNotFound,
                          self.dbapi.unset_server_tags, self.context, '123')

    def test_add_server_tag(self):
        tag = self.dbapi.add_server_tag(self.context, self.server.id, 'tag1')
        self.assertEqual(self.server.id, tag.server_id)
        self.assertEqual('tag1', tag.tag)

    def test_add_server_tag_duplicate(self):
        tag = self.dbapi.add_server_tag(self.context, self.server.id, 'tag1')
        tag = self.dbapi.add_server_tag(self.context, self.server.id, 'tag1')
        self.assertEqual(self.server.id, tag.server_id)
        self.assertEqual('tag1', tag.tag)

    def test_add_server_tag_server_not_exist(self):
        self.assertRaises(exception.ServerNotFound,
                          self.dbapi.add_server_tag, self.context,
                          '123', 'tag1')

    def test_delete_server_tag(self):
        self.dbapi.set_server_tags(self.context, self.server.id,
                                   ['tag1', 'tag2'])
        self.dbapi.delete_server_tag(self.context, self.server.id, 'tag1')
        tags = self.dbapi.get_server_tags_by_server_id(self.context,
                                                       self.server.id)
        self.assertEqual(1, len(tags))
        self.assertEqual('tag2', tags[0].tag)

    def test_delete_server_tag_not_found(self):
        self.assertRaises(exception.ServerTagNotFound,
                          self.dbapi.delete_server_tag, self.context,
                          self.server.id, 'tag1')

    def test_delete_server_tag_server_not_found(self):
        self.assertRaises(exception.ServerNotFound,
                          self.dbapi.delete_server_tag, self.context,
                          '123', 'tag1')

    def test_server_tag_exists(self):
        self.dbapi.set_server_tags(self.context,
                                   self.server.id, ['tag1', 'tag2'])
        ret = self.dbapi.server_tag_exists(self.context,
                                           self.server.id, 'tag1')
        self.assertTrue(ret)

    def test_server_tag_not_exists(self):
        ret = self.dbapi.server_tag_exists(self.context,
                                           self.server.id, 'tag1')
        self.assertFalse(ret)
