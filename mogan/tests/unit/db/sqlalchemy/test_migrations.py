# Copyright 2010-2011 OpenStack Foundation
# Copyright 2012-2013 IBM Corp.
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

"""
Tests for database migrations. There are "opportunistic" tests for both mysql
and postgresql in here, which allows testing against these databases in a
properly configured unit test environment.

For the opportunistic testing you need to set up a db named 'openstack_citest'
with user 'openstack_citest' and password 'openstack_citest' on localhost.
The test will then use that db and u/p combo to run the tests.

For postgres on Ubuntu this can be done with the following commands:

::

 sudo -u postgres psql
 postgres=# create user openstack_citest with createdb login password
      'openstack_citest';
 postgres=# create database openstack_citest with owner openstack_citest;

"""

import contextlib

from alembic import script
import mock
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log as logging
import sqlalchemy
import sqlalchemy.exc

from mogan.db.sqlalchemy import migration
from mogan.db.sqlalchemy import models
from mogan.tests import base

LOG = logging.getLogger(__name__)


def _get_connect_string(backend, user, passwd, database):
    """Get database connection

    Try to get a connection with a very specific set of values, if we get
    these then we'll run the tests, otherwise they are skipped
    """
    if backend == "postgres":
        backend = "postgresql+psycopg2"
    elif backend == "mysql":
        backend = "mysql+mysqldb"
    else:
        raise Exception("Unrecognized backend: '%s'" % backend)

    return ("%(backend)s://%(user)s:%(passwd)s@localhost/%(database)s"
            % {'backend': backend, 'user': user, 'passwd': passwd,
               'database': database})


def _is_backend_avail(backend, user, passwd, database):
    try:
        connect_uri = _get_connect_string(backend, user, passwd, database)
        engine = sqlalchemy.create_engine(connect_uri)
        connection = engine.connect()
    except Exception:
        # intentionally catch all to handle exceptions even if we don't
        # have any backend code loaded.
        return False
    else:
        connection.close()
        engine.dispose()
        return True


@contextlib.contextmanager
def patch_with_engine(engine):
    with mock.patch.object(enginefacade.get_legacy_facade(),
                           'get_engine') as patch_engine:
        patch_engine.return_value = engine
        yield


class WalkVersionsMixin(object):
    def _walk_versions(self, engine=None, alembic_cfg=None):
        # Determine latest version script from the repo, then
        # upgrade from 1 through to the latest, with no data
        # in the databases. This just checks that the schema itself
        # upgrades successfully.

        # Place the database under version control
        with patch_with_engine(engine):

            script_directory = script.ScriptDirectory.from_config(alembic_cfg)

            self.assertIsNone(self.migration_api.version(alembic_cfg))

            versions = [ver for ver in script_directory.walk_revisions()]

            for version in reversed(versions):
                self._migrate_up(engine, alembic_cfg,
                                 version.revision, with_data=True)

    def _migrate_up(self, engine, config, version, with_data=False):
        """migrate up to a new version of the db.

        We allow for data insertion and post checks at every
        migration version with special _pre_upgrade_### and
        _check_### functions in the main test.
        """
        # NOTE(sdague): try block is here because it's impossible to debug
        # where a failed data migration happens otherwise
        try:
            if with_data:
                data = None
                pre_upgrade = getattr(
                    self, "_pre_upgrade_%s" % version, None)
                if pre_upgrade:
                    data = pre_upgrade(engine)

            self.migration_api.upgrade(version, config=config)
            self.assertEqual(version, self.migration_api.version(config))
            if with_data:
                check = getattr(self, "_check_%s" % version, None)
                if check:
                    check(engine, data)
        except Exception:
            LOG.error("Failed to migrate to version %(version)s on engine "
                      "%(engine)s",
                      {'version': version, 'engine': engine})
            raise


class TestWalkVersions(base.TestCase, WalkVersionsMixin):
    def setUp(self):
        super(TestWalkVersions, self).setUp()
        self.migration_api = mock.MagicMock()
        self.engine = mock.MagicMock()
        self.config = mock.MagicMock()
        self.versions = [mock.Mock(revision='2b2'), mock.Mock(revision='1a1')]

    def test_migrate_up(self):
        self.migration_api.version.return_value = 'dsa123'

        self._migrate_up(self.engine, self.config, 'dsa123')

        self.migration_api.upgrade.assert_called_with('dsa123',
                                                      config=self.config)
        self.migration_api.version.assert_called_with(self.config)

    def test_migrate_up_with_data(self):
        test_value = {"a": 1, "b": 2}
        self.migration_api.version.return_value = '141'
        self._pre_upgrade_141 = mock.MagicMock()
        self._pre_upgrade_141.return_value = test_value
        self._check_141 = mock.MagicMock()

        self._migrate_up(self.engine, self.config, '141', True)

        self._pre_upgrade_141.assert_called_with(self.engine)
        self._check_141.assert_called_with(self.engine, test_value)

    @mock.patch.object(script, 'ScriptDirectory')
    @mock.patch.object(WalkVersionsMixin, '_migrate_up')
    def test_walk_versions_all_default(self, _migrate_up, script_directory):
        fc = script_directory.from_config()
        fc.walk_revisions.return_value = self.versions
        self.migration_api.version.return_value = None

        self._walk_versions(self.engine, self.config)

        self.migration_api.version.assert_called_with(self.config)

        upgraded = [mock.call(self.engine, self.config, v.revision,
                    with_data=True) for v in reversed(self.versions)]
        self.assertEqual(self._migrate_up.call_args_list, upgraded)

    @mock.patch.object(script, 'ScriptDirectory')
    @mock.patch.object(WalkVersionsMixin, '_migrate_up')
    def test_walk_versions_all_false(self, _migrate_up, script_directory):
        fc = script_directory.from_config()
        fc.walk_revisions.return_value = self.versions
        self.migration_api.version.return_value = None

        self._walk_versions(self.engine, self.config)

        upgraded = [mock.call(self.engine, self.config, v.revision,
                    with_data=True) for v in reversed(self.versions)]
        self.assertEqual(upgraded, self._migrate_up.call_args_list)


class MigrationCheckersMixin(object):

    def setUp(self):
        super(MigrationCheckersMixin, self).setUp()
        self.config = migration._alembic_config()
        self.migration_api = migration

    def test_walk_versions(self):
        self._walk_versions(self.engine, self.config)

    def test_connect_fail(self):
        """Test that we can trigger a database connection failure

        Test that we can fail gracefully to ensure we don't break people
        without specific database backend
        """
        if _is_backend_avail(self.FIXTURE.DRIVER, "openstack_cifail",
                             self.FIXTURE.USERNAME, self.FIXTURE.DBNAME):
            self.fail("Shouldn't have connected")

    def _check_91941bf1ebc9(self, engine, data):
        nodes = db_utils.get_table(engine, 'servers')
        col_names = [column.name for column in nodes.c]
        self.assertIn('created_at', col_names)
        self.assertIsInstance(nodes.c.provision_updated_at.type,
                              sqlalchemy.types.DateTime)
        nodes = db_utils.get_table(engine, 'quotas')
        col_names = [column.name for column in nodes.c]
        self.assertIn('created_at', col_names)
        self.assertIsInstance(nodes.c.resource_name.type,
                              sqlalchemy.types.String)
        nodes = db_utils.get_table(engine, 'quota_usages')
        col_names = [column.name for column in nodes.c]
        self.assertIn('created_at', col_names)
        self.assertIsInstance(nodes.c.resource_name.type,
                              sqlalchemy.types.String)
        nodes = db_utils.get_table(engine, 'reservations')
        col_names = [column.name for column in nodes.c]
        self.assertIn('created_at', col_names)
        self.assertIsInstance(nodes.c.resource_name.type,
                              sqlalchemy.types.String)

    def test_upgrade_and_version(self):
        with patch_with_engine(self.engine):
            self.migration_api.upgrade('head')
            self.assertIsNotNone(self.migration_api.version())

    def test_create_schema_and_version(self):
        with patch_with_engine(self.engine):
            self.migration_api.create_schema()
            self.assertIsNotNone(self.migration_api.version())

    def test_upgrade_and_create_schema(self):
        with patch_with_engine(self.engine):
            self.migration_api.upgrade('31baaf680d2b')
            self.assertRaises(db_exc.DbMigrationError,
                              self.migration_api.create_schema)

    def test_upgrade_twice(self):
        with patch_with_engine(self.engine):
            self.migration_api.upgrade('31baaf680d2b')
            v1 = self.migration_api.version()
            self.migration_api.upgrade('head')
            v2 = self.migration_api.version()
            self.assertNotEqual(v1, v2)


class TestMigrationsMySQL(MigrationCheckersMixin,
                          WalkVersionsMixin,
                          test_base.MySQLOpportunisticTestCase):
    pass


class TestMigrationsPostgreSQL(MigrationCheckersMixin,
                               WalkVersionsMixin,
                               test_base.PostgreSQLOpportunisticTestCase):
    pass


class ModelsMigrationSyncMixin(object):

    def get_metadata(self):
        return models.Base.metadata

    def get_engine(self):
        return self.engine

    def db_sync(self, engine):
        with patch_with_engine(engine):
            migration.upgrade('head')


class ModelsMigrationsSyncMysql(ModelsMigrationSyncMixin,
                                test_migrations.ModelsMigrationsSync,
                                test_base.MySQLOpportunisticTestCase):
    pass


class ModelsMigrationsSyncPostgres(ModelsMigrationSyncMixin,
                                   test_migrations.ModelsMigrationsSync,
                                   test_base.PostgreSQLOpportunisticTestCase):
    pass
