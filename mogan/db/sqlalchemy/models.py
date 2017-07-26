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
from sqlalchemy import (Boolean, Column, DateTime, Enum, ForeignKey,
                        Index, Text)
from sqlalchemy import orm
from sqlalchemy import schema, String, Integer
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext.declarative import declarative_base

from mogan.common import paths
from mogan.conf import CONF

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('mogan.sqlite')


db_options.set_defaults(CONF, connection=_DEFAULT_SQL_CONNECTION)


def MediumText():
    return Text().with_variant(MEDIUMTEXT(), 'mysql')


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': 'InnoDB',
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


class Server(Base):
    """Represents possible types for servers."""

    __tablename__ = 'servers'
    __table_args__ = (
        Index('servers_project_id_idx', 'project_id'),
        schema.UniqueConstraint('uuid', name='uniq_servers0uuid'),
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
    flavor_uuid = Column(String(36), nullable=True)
    availability_zone = Column(String(255), nullable=True)
    image_uuid = Column(String(36), nullable=True)
    node_uuid = Column(String(36), nullable=True)
    launched_at = Column(DateTime, nullable=True)
    extra = Column(db_types.JsonEncodedDict)
    locked = Column(Boolean)
    locked_by = Column(Enum('owner', 'admin'))


class ServerNic(Base):
    """Represents the NIC info for servers."""

    __tablename__ = 'server_nics'
    __table_args__ = (
        Index('server_nics_server_uuid_idx', 'server_uuid'),
        table_args()
    )
    server_uuid = Column(String(36), ForeignKey('servers.uuid'))
    port_id = Column(String(36), primary_key=True)
    mac_address = Column(String(32), nullable=False)
    network_id = Column(String(36), nullable=True)
    fixed_ips = Column(db_types.JsonEncodedList)
    floating_ip = Column(String(64), nullable=True)
    _server = orm.relationship(
        Server,
        backref=orm.backref('server_nics', uselist=False),
        foreign_keys=server_uuid,
        primaryjoin='Server.uuid == ServerNic.server_uuid')


class ServerFault(Base):
    """Represents fault info for server"""

    __tablename__ = "server_faults"
    __table_args__ = (
        Index('server_faults_server_uuid_idx', 'server_uuid'),
        table_args()
    )

    id = Column(Integer, primary_key=True, nullable=False)
    server_uuid = Column(String(36), ForeignKey('servers.uuid'))
    code = Column(Integer(), nullable=False)
    message = Column(String(255))
    detail = Column(MediumText())
    server = orm.relationship(
        Server,
        backref=orm.backref('server_faults', uselist=False),
        foreign_keys=server_uuid,
        primaryjoin='Server.uuid == ServerFault.server_uuid')


class Flavors(Base):
    """Represents possible types for servers."""

    __tablename__ = 'flavors'
    __table_args__ = (
        schema.UniqueConstraint("uuid", name="uniq_flavors0uuid"),
        schema.UniqueConstraint("name", name="uniq_flavors0name"),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(MediumText())
    resources = Column(db_types.JsonEncodedDict)
    resource_traits = Column(db_types.JsonEncodedDict)
    is_public = Column(Boolean, default=True)
    disabled = Column(Boolean, default=False)
    servers = orm.relationship(
        Server,
        backref=orm.backref('flavor', uselist=False),
        foreign_keys=uuid,
        primaryjoin='Server.flavor_uuid == Flavors.uuid')


class FlavorProjects(Base):
    """Represents projects associated flavors."""

    __tablename__ = 'flavor_projects'
    __table_args__ = (
        schema.UniqueConstraint(
            'flavor_id', 'project_id',
            name='uniq_flavor_projects0flavor_id0project_id'
        ),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    flavor_id = Column(Integer, ForeignKey('flavors.id'),
                       nullable=True)
    project_id = Column(String(36), nullable=True)
    flavors = orm.relationship(
        Flavors,
        backref=orm.backref('projects', uselist=False),
        foreign_keys=flavor_id,
        primaryjoin='FlavorProjects.flavor_id'
                    ' == Flavors.id')


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
    hard_limit = Column(Integer, default=0)
    allocated = Column(Integer, default=0)


class QuotaUsage(Base):
    """Represents the current usage for a given resource."""

    __tablename__ = 'quota_usages'
    __table_args__ = (
        schema.UniqueConstraint('resource_name', 'project_id',
                                name='uniq_quotas0resource_name'),
        Index('quota_usage_project_id_idx', 'project_id'),
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
        Index('reservations_project_id_idx', 'project_id'),
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


class KeyPair(Base):
    """Represents a public key pair for ssh / WinRM."""
    __tablename__ = 'key_pairs'
    __table_args__ = (
        schema.UniqueConstraint("user_id", "name",
                                name="uniq_key_pairs0user_id0name"),
    )
    id = Column(Integer, primary_key=True, nullable=False)

    name = Column(String(255), nullable=False)

    user_id = Column(String(255), nullable=False)

    project_id = Column(String(255), nullable=False)

    fingerprint = Column(String(255))
    public_key = Column(Text())
    type = Column(Enum('ssh', 'x509', name='keypair_types'),
                  nullable=False, server_default='ssh')


class AggregateMetadata(Base):
    """Represents possible types for aggregate metadata."""

    __tablename__ = 'aggregate_metadata'
    __table_args__ = (
        schema.UniqueConstraint(
            'aggregate_id', 'key',
            name='uniq_aggregate_metadata0aggregate_id0key'),
        Index('aggregate_metadata_key_idx', 'key'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)
    aggregate_id = Column(Integer, ForeignKey('aggregates.id'), nullable=False)


class Aggregate(Base):
    """Represents possible types for aggregates."""

    __tablename__ = 'aggregates'
    __table_args__ = (
        Index('aggregate_uuid_idx', 'uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    _metadata = orm.relationship(
        AggregateMetadata,
        primaryjoin='and_('
        'Aggregate.id == AggregateMetadata.aggregate_id)')

    @property
    def _extra_keys(self):
        return ['metadetails']

    @property
    def metadetails(self):
        return {m.key: m.value for m in self._metadata}


class ServerGroupMember(Base):
    """Represents the members for a server group."""
    __tablename__ = 'server_group_member'
    __table_args__ = (
        Index('server_group_member_server_idx', 'server_uuid'),
    )
    id = Column(Integer, primary_key=True, nullable=False)
    server_uuid = Column(String(255))
    group_id = Column(Integer, ForeignKey('server_groups.id'),
                      nullable=False)


class ServerGroupPolicy(Base):
    """Represents the policy type for a server group."""
    __tablename__ = 'server_group_policy'
    __table_args__ = (
        Index('server_group_policy_policy_idx', 'policy'),
    )
    id = Column(Integer, primary_key=True, nullable=False)
    policy = Column(String(255))
    group_id = Column(Integer, ForeignKey('server_groups.id'),
                      nullable=False)


class ServerGroup(Base):
    """Represents a server group.

    A group will maintain a collection of servers and the relationship
    between them.
    """

    __tablename__ = 'server_groups'
    __table_args__ = (
        schema.UniqueConstraint("uuid",
                                name="uniq_server_groups0uuid"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255))
    project_id = Column(String(255))
    uuid = Column(String(36), nullable=False)
    name = Column(String(255))
    _policies = orm.relationship(
        ServerGroupPolicy,
        primaryjoin='ServerGroup.id == ServerGroupPolicy.group_id')
    _members = orm.relationship(
        ServerGroupMember,
        primaryjoin='ServerGroup.id == ServerGroupMember.group_id')

    @property
    def policies(self):
        return [p.policy for p in self._policies]

    @property
    def members(self):
        return [m.server_uuid for m in self._members]
