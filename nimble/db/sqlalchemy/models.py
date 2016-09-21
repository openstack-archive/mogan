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
from sqlalchemy import Boolean, Column, ForeignKey
from sqlalchemy import orm
from sqlalchemy import schema, String, Integer, Text
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


class InstanceTypes(Base):
    """Represents possible types for instances."""

    __tablename__ = 'instance_types'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_instance_types0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    is_public = Column(Boolean, default=True)


class InstanceTypeProjects(Base):
    """Represents projects associated instance_types."""

    __tablename__ = 'instance_type_projects'
    __table_args__ = (
        schema.UniqueConstraint(
            'instance_type_id', 'project_id',
            name='uniq_instance_type_projects0instance_type_id0project_id'
        ),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    instance_type_id = Column(Integer, nullable=True)
    project_id = Column(String(36), nullable=True)


class InstanceTypeExtraSpecs(Base):
    """Represents additional specs as key/value pairs for an instance_type."""
    __tablename__ = 'instance_type_extra_specs'
    __table_args__ = (
        schema.UniqueConstraint(
              "instance_type_id", "key",
              name=("uniq_instance_type_extra_specs0"
                    "instance_type_id")
        ),
        {'mysql_collate': 'utf8_bin'},
    )
    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(255))
    instance_type_id = Column(Integer, ForeignKey('instance_types.id'),
                              nullable=False)
    instance_type = orm.relationship(InstanceTypes, backref="extra_specs",
                 foreign_keys=instance_type_id,
                 primaryjoin='and_('
                 'InstanceTypeExtraSpecs.instance_type_id == InstanceTypes.id)')


class Instance(Base):
    """Represents possible types for instances."""

    __tablename__ = 'instances'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_instances0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(String(255), nullable=True)
    power_state = Column(String(255), nullable=True)
    task_state = Column(String(255), nullable=True)
    instance_type_id = Column(Integer, nullable=True)
    availability_zone = Column(String(255), nullable=True)
    image_uuid = Column(String(36), nullable=True)
    network_uuid = Column(String(36), nullable=True)
    node_uuid = Column(String(36), nullable=True)
    extra = Column(Text, nullable=True)
