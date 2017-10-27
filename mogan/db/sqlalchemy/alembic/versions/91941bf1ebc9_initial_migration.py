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

"""initial migration

Revision ID: 91941bf1ebc9
Revises: None
Create Date: 2016-08-17 15:17:39.892804

"""

# revision identifiers, used by Alembic.
revision = '91941bf1ebc9'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'flavors',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resources', sa.Text(), nullable=True),
        sa.Column('resource_traits', sa.Text(), nullable=True),
        sa.Column('resource_aggregates', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_flavors0uuid'),
        sa.UniqueConstraint('name', name='uniq_flavors0name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_projects',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flavor_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['flavor_id'],
                                ['flavors.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flavor_id', 'project_id',
                            name='uniq_flavor_projects0flavor_id0project_id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'servers',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('power_state', sa.String(length=15), nullable=True),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=True),
        sa.Column('image_uuid', sa.String(length=36), nullable=True),
        sa.Column('launched_at', sa.DateTime(), nullable=True),
        sa.Column('availability_zone', sa.String(length=255), nullable=True),
        sa.Column('node', sa.String(length=255), nullable=True),
        sa.Column('node_uuid', sa.String(length=36), nullable=True),
        sa.Column('extra', sa.Text(), nullable=True),
        sa.Column('partitions', sa.Text(), nullable=True),
        sa.Column('affinity_zone', sa.String(length=255), nullable=True),
        sa.Column('locked_by', sa.Enum('admin', 'owner'), nullable=True),
        sa.Column('key_name', sa.String(length=255), nullable=True),
        sa.Column('system_metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_servers0uuid'),
        sa.Index('servers_project_id_idx', 'project_id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'server_nics',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('server_uuid', sa.String(length=36),
                  sa.ForeignKey('servers.uuid'), nullable=True),
        sa.Column('port_id', sa.String(length=36), nullable=False),
        sa.Column('mac_address', sa.String(length=36), nullable=False),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('floating_ip', sa.String(length=64), nullable=True),
        sa.Column('fixed_ips', sa.Text(), nullable=True),
        sa.Column('preserve_on_delete', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('port_id'),
        sa.Index('server_nics_server_uuid_idx', 'server_uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'server_faults',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_uuid', sa.String(length=36), nullable=True),
        sa.Column('code', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('message', sa.String(length=255), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['server_uuid'], ['servers.uuid']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('server_faults_server_uuid_idx', 'server_uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'quotas',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('resource_name', sa.String(length=255), nullable=False),
        sa.Column('hard_limit', sa.Integer(), nullable=True),
        sa.Column('allocated', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource_name', 'project_id',
                            name='uniq_quotas0resource_name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'quota_usages',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('in_use', sa.Integer(), nullable=True),
        sa.Column('reserved', sa.Integer(), nullable=True),
        sa.Column('until_refresh', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource_name', 'project_id',
                            name='uniq_quota_usages0resource_name'),
        sa.Index('quota_usage_project_id_idx', 'project_id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'reservations',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('usage_id', sa.Integer(), nullable=True),
        sa.Column('allocated_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('delta', sa.Integer(), nullable=True),
        sa.Column('expire', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['usage_id'],
                                ['quota_usages.id']),
        sa.ForeignKeyConstraint(['allocated_id'],
                                ['quotas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('reservations_project_id_idx', 'project_id'),
        sa.UniqueConstraint('uuid', name='uniq_reservation0uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'key_pairs',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('fingerprint', sa.String(255)),
        sa.Column('public_key', sa.Text()),
        sa.Column('type', sa.Enum('ssh', 'x509'), nullable=False,
                  default='ssh'),
        sa.UniqueConstraint('user_id', 'name',
                            name="uniq_key_pairs0user_id0name"),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    op.create_table(
        'aggregates',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'aggregate_metadata',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('aggregate_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['aggregate_id'],
                                ['aggregates.id']),
        sa.UniqueConstraint('aggregate_id', 'key',
                            name='uniq_aggregate_metadata0aggregate_id0key'),
        sa.Index('aggregate_metadata_key_idx', 'key'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'server_groups',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_server_groups0uuid'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    op.create_table(
        'server_group_policy',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('policy', sa.String(length=36), nullable=True),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('server_groups.id'),
                  nullable=False),
        sa.Index('server_group_policy_policy_idx', 'policy'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    op.create_table(
        'server_group_member',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('server_uuid', sa.String(length=36), nullable=True),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('server_groups.id'),
                  nullable=False),
        sa.Index('server_group_member_server_idx', 'server_uuid'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    op.create_table(
        'server_tags',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('server_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('server_id', 'tag'),
        sa.ForeignKeyConstraint(['server_id'],
                                ['servers.id']),
        sa.Index('server_tags_tag_idx', 'tag'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
