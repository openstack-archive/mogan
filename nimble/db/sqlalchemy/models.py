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

"""
SQLAlchemy models for baremetal compute service.
"""

from oslo_db import options as db_options
from oslo_db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy.ext.declarative import declarative_base

from nimble.common import paths
from nimble.conf import CONF

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('nimble.sqlite')


db_options.set_defaults(CONF, _DEFAULT_SQL_CONNECTION, 'nimble.sqlite')


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class NimbleBase(models.TimestampMixin,
                 models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative_base(cls=NimbleBase)
