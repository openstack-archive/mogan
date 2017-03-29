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
from oslo_db.sqlalchemy import types as db_types
import six.moves.urllib.parse as urlparse
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy import orm
from sqlalchemy import schema, String, Integer
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base

from mogan.common import paths
from mogan.conf import CONF

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('mogan.sqlite')


db_options.set_defaults(CONF, _DEFAULT_SQL_CONNECTION)


def MediumText():
    return Text().with_variant(MEDIUMTEXT(), 'mysql')


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class MoganBase(models.TimestampMixin,
                models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative_base(cls=MoganBase)


class Instance(Base):
    """Represents possible types for instances."""

    __tablename__ = 'instances'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_instances0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    project_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True)
    status = Column(String(255), nullable=True)
    power_state = Column(String(15), nullable=True)
    instance_type_uuid = Column(String(36), nullable=True)
    availability_zone = Column(String(255), nullable=True)
    image_uuid = Column(String(36), nullable=True)
    node_uuid = Column(String(36), nullable=True)
    launched_at = Column(DateTime, nullable=True)
    extra = Column(db_types.JsonEncodedDict)
    locked = Column(Boolean)
    locked_by = Column(Enum('owner', 'admin'))


class ComputeNode(Base):
    """Represents the compute nodes."""

    __tablename__ = 'compute_nodes'
    __table_args__ = (
        schema.UniqueConstraint('node_uuid',
                                name='uniq_compute_nodes0node_uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    cpus = Column(Integer, nullable=False)
    memory_mb = Column(Integer, nullable=False)
    hypervisor_type = Column(String(255), nullable=False)
    node_type = Column(String(255), nullable=False)
    availability_zone = Column(String(255), nullable=True)
    node_uuid = Column(String(36), nullable=False)
    extra_specs = Column(db_types.JsonEncodedDict)
    used = Column(Boolean, default=False)


class ComputePort(Base):
    """Represents the compute ports."""

    __tablename__ = 'compute_ports'
    __table_args__ = (
        schema.UniqueConstraint('port_uuid',
                                name='uniq_compute_ports0port_uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    address = Column(String(18), nullable=False)
    port_type = Column(String(255), nullable=False)
    port_uuid = Column(String(36), nullable=False)
    node_uuid = Column(String(36), nullable=False)
    extra_specs = Column(db_types.JsonEncodedDict)
    _node = orm.relationship(
        "ComputeNode",
        backref='ports',
        foreign_keys=node_uuid,
        primaryjoin='ComputeNode.node_uuid == ComputePort.node_uuid')


class InstanceNic(Base):
    """Represents the NIC info for instances."""

    __tablename__ = 'instance_nics'
    instance_uuid = Column(String(36), nullable=True)
    port_id = Column(String(36), primary_key=True)
    mac_address = Column(String(32), nullable=False)
    network_id = Column(String(36), nullable=True)
    fixed_ips = Column(db_types.JsonEncodedList)
    port_type = Column(String(64), nullable=True)
    floating_ip = Column(String(64), nullable=True)
    _instance = orm.relationship(
        Instance,
        backref=orm.backref('instance_nics', uselist=False),
        foreign_keys=instance_uuid,
        primaryjoin='Instance.uuid == InstanceNic.instance_uuid')


class InstanceTypes(Base):
    """Represents possible types for instances."""

    __tablename__ = 'instance_types'
    uuid = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=True)
    instances = orm.relationship(
        Instance,
        backref=orm.backref('instance_type', uselist=False),
        foreign_keys=uuid,
        primaryjoin='Instance.instance_type_uuid == InstanceTypes.uuid')


class InstanceTypeProjects(Base):
    """Represents projects associated instance_types."""

    __tablename__ = 'instance_type_projects'
    __table_args__ = (
        schema.UniqueConstraint(
            'instance_type_uuid', 'project_id',
            name='uniq_instance_type_projects0instance_type_uuid0project_id'
        ),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    instance_type_uuid = Column(Integer, nullable=True)
    project_id = Column(String(36), nullable=True)
    instances = orm.relationship(
        InstanceTypes,
        backref=orm.backref('projects', uselist=False),
        foreign_keys=instance_type_uuid,
        primaryjoin='InstanceTypeProjects.instance_type_uuid'
                    ' == InstanceTypes.uuid')


class InstanceTypeExtraSpecs(Base):
    """Represents additional specs as key/value pairs for an instance_type."""
    __tablename__ = 'instance_type_extra_specs'
    __table_args__ = (
        schema.UniqueConstraint(
            "instance_type_uuid", "key",
            name=("uniq_instance_type_extra_specs0"
                  "instance_type_uuid")
        ),
        {'mysql_collate': 'utf8_bin'},
    )
    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(255))
    instance_type_uuid = Column(String(36), ForeignKey('instance_types.uuid'),
                                nullable=False)
    instance_type = orm.relationship(
        InstanceTypes, backref="extra_specs",
        foreign_keys=instance_type_uuid,
        primaryjoin='InstanceTypeExtraSpecs.instance_type_uuid '
                    '== InstanceTypes.uuid')


class InstanceFault(Base):
    """Represents fault info for instance"""

    __tablename__ = "instance_faults"

    id = Column(Integer, primary_key=True, nullable=False)
    instance_uuid = Column(String(36),
                           ForeignKey('instances.uuid'))
    code = Column(Integer(), nullable=False)
    message = Column(String(255))
    detail = Column(MediumText())
    instance = orm.relationship(
        Instance,
        backref=orm.backref('instance_faults', uselist=False),
        foreign_keys=instance_uuid,
        primaryjoin='Instance.uuid == InstanceFault.instance_uuid')


class Quota(Base):
    """Represents a single quota override for a project."""

    __tablename__ = 'quotas'
    __table_args__ = (
        schema.UniqueConstraint('resource_name', 'project_id',
                                name='uniq_quotas0resource_name'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    resource_name = Column(String(255), nullable=False)
    project_id = Column(String(36), nullable=False)
    hard_limit = Column(Integer, nullable=False)
    allocated = Column(Integer, default=0)


class QuotaUsage(Base):
    """Represents the current usage for a given resource."""

    __tablename__ = 'quota_usages'
    __table_args__ = (
        schema.UniqueConstraint('resource_name', 'project_id',
                                name='uniq_quotas0resource_name'),
        table_args()
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(String(255), index=True)
    resource_name = Column(String(255))
    in_use = Column(Integer)
    reserved = Column(Integer)
    until_refresh = Column(Integer, nullable=True)

    @property
    def total(self):
        return self.in_use + self.reserved


class Reservation(Base):
    """Represents a resource reservation for quotas."""

    __tablename__ = 'reservations'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_reservation0uuid'),
        table_args()
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=False)
    usage_id = Column(Integer, ForeignKey('quota_usages.id'), nullable=True)
    allocated_id = Column(Integer, ForeignKey('quotas.id'), nullable=True)
    project_id = Column(String(255), index=True)
    resource_name = Column(String(255))
    delta = Column(Integer)
    expire = Column(DateTime, nullable=False)

    usage = orm.relationship(
        "QuotaUsage", foreign_keys=usage_id,
        primaryjoin='Reservation.usage_id == QuotaUsage.id')

    quota = orm.relationship(
        "Quota", foreign_keys=allocated_id,
        primaryjoin='Reservation.allocated_id == Quota.id')
