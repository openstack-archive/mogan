# Copyright 2016 Huawei Technologies Co.,LTD.
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

"""Mogan DB test base class."""

import fixtures
from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade

from mogan.db import api as dbapi
from mogan.db.sqlalchemy import migration
from mogan.db.sqlalchemy import models
from mogan.tests import base


CONF = cfg.CONF

_DB_CACHE = None


class Database(fixtures.Fixture):

    def __init__(self, engine, db_migrate, sql_connection):
        self.sql_connection = sql_connection

        self.engine = engine
        self.engine.dispose()
        conn = self.engine.connect()
        self.setup_sqlite(db_migrate)

        self.post_migrations()
        self._DB = "".join(line for line in conn.connection.iterdump())
        self.engine.dispose()

    def setup_sqlite(self, db_migrate):
        if db_migrate.version():
            return
        models.Base.metadata.create_all(self.engine)
        db_migrate.stamp('head')

    def setUp(self):
        super(Database, self).setUp()

        conn = self.engine.connect()
        conn.connection.executescript(self._DB)
        self.addCleanup(self.engine.dispose)

    def post_migrations(self):
        """Any addition steps that are needed outside of the migrations."""


class DbTestCase(base.TestCase):

    def setUp(self):
        super(DbTestCase, self).setUp()

        self.dbapi = dbapi.get_instance()

        global _DB_CACHE
        if not _DB_CACHE:
            engine = enginefacade.get_legacy_facade().get_engine()
            _DB_CACHE = Database(engine, migration,
                                 sql_connection=CONF.database.connection)
        self.useFixture(_DB_CACHE)

    def _dict_from_object(self, obj, ignored_keys):
        if ignored_keys is None:
            ignored_keys = []

        return {k: v for k, v in obj.items()
                if k not in ignored_keys}

    def _assertDickeysEqual(self, obj1_dic, obj2_dic, msg=None):
        obj1_keys = set(obj1_dic.keys())
        obj2_keys = set(obj2_dic.keys())

        difference1 = obj1_keys.difference(obj2_keys)
        difference2 = obj2_keys.difference(obj1_keys)

        if not (difference1 or difference2):
            return

        lines = []
        if difference1:
            lines.append('Keys in the first obj but not the second:')
            for item in difference1:
                lines.append(repr(item))
        if difference2:
            lines.append('Keys in the second obj but not the first:')
            for item in difference2:
                lines.append(repr(item))
        standardMsg = '\n'.join(lines)
        self.fail(self._formatMessage(msg, standardMsg))

    def _assertEqualObjects(self, obj1, obj2, ignored_keys=None):
        obj1 = self._dict_from_object(obj1, ignored_keys)
        obj2 = self._dict_from_object(obj2, ignored_keys)

        self._assertDickeysEqual(obj1, obj2)
        self.assertDictEqual(obj1, obj2)

    def _assertEqualListsOfObjects(self, objs1, objs2, ignored_keys=None):
        obj_to_dict = lambda o: self._dict_from_object(o, ignored_keys)
        sort_key = lambda d: [d[k] for k in sorted(d)]
        conv_and_sort = lambda obj: sorted(map(obj_to_dict, obj), key=sort_key)
        self.assertListEqual(conv_and_sort(objs1), conv_and_sort(objs2))

    def _assertEqualOrderedListOfObjects(self, objs1, objs2,
                                         ignored_keys=None):
        conv = lambda objs:\
            [self._dict_from_object(obj, ignored_keys) for obj in objs]

        self.assertListEqual(conv(objs1), conv(objs2))
