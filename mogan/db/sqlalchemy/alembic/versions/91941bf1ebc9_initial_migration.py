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
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_extra_specs',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_projects',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_cpus',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('cores', sa.Integer(), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_memory',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=255), nullable=True),
        sa.Column('size_mb', sa.Integer(), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_disks',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=255), nullable=True),
        sa.Column('size_gb', sa.Integer(), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'flavor_nics',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=255), nullable=True),
        sa.Column('speed', sa.String(length=255), nullable=False),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['flavor_uuid'],
                                ['flavors.uuid']),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'servers',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('power_state', sa.String(length=15), nullable=True),
        sa.Column('flavor_uuid', sa.String(length=36), nullable=True),
        sa.Column('image_uuid', sa.String(length=36), nullable=True),
        sa.Column('launched_at', sa.DateTime(), nullable=True),
        sa.Column('availability_zone', sa.String(length=255), nullable=True),
        sa.Column('node_uuid', sa.String(length=36), nullable=True),
        sa.Column('extra', sa.Text(), nullable=True),
        sa.Column('locked', sa.Boolean(), nullable=True),
        sa.Column('locked_by', sa.Enum('admin', 'owner'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_servers0uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'compute_nodes',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cpus', sa.Integer(), nullable=False),
        sa.Column('memory_mb', sa.Integer(), nullable=False),
        sa.Column('hypervisor_type', sa.String(length=255), nullable=False),
        sa.Column('resource_class', sa.String(length=80), nullable=False),
        sa.Column('availability_zone', sa.String(length=255), nullable=True),
        sa.Column('node_uuid', sa.String(length=36), nullable=False),
        sa.Column('extra_specs', sa.Text(), nullable=True),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('node_uuid', name='uniq_compute_nodes0node_uuid'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'compute_ports',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(length=18), nullable=False),
        sa.Column('port_type', sa.String(length=255), nullable=False),
        sa.Column('port_uuid', sa.String(length=36), nullable=False),
        sa.Column('node_uuid', sa.String(length=36), nullable=False),
        sa.Column('extra_specs', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('port_uuid', name='uniq_compute_ports0port_uuid'),
        sa.ForeignKeyConstraint(['node_uuid'], ['compute_nodes.node_uuid'], ),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'compute_disks',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('disk_type', sa.String(length=255), nullable=False),
        sa.Column('size_gb', sa.Integer(), nullable=False),
        sa.Column('disk_uuid', sa.String(length=36), nullable=False),
        sa.Column('node_uuid', sa.String(length=36), nullable=False),
        sa.Column('extra_specs', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('disk_uuid', name='uniq_compute_disks0disk_uuid'),
        sa.ForeignKeyConstraint(['node_uuid'], ['compute_nodes.node_uuid'], ),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'server_nics',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('server_uuid', sa.String(length=36), nullable=False),
        sa.Column('port_id', sa.String(length=36), nullable=False),
        sa.Column('mac_address', sa.String(length=36), nullable=True),
        sa.Column('network_id', sa.String(length=36), nullable=True),
        sa.Column('port_type', sa.String(length=64), nullable=True),
        sa.Column('floating_ip', sa.String(length=64), nullable=True),
        sa.Column('fixed_ips', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['server_uuid'], ['servers.uuid'], ),
        sa.PrimaryKeyConstraint('port_id'),
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
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'quotas',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
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
                            name='uniq_quotas_usages0resource_name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'reservations',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('usage_id', sa.Integer(), nullable=True),
        sa.Column('allocated_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('delta', sa.Integer(), nullable=True),
        sa.Column('expire', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['usage_id'],
                                ['quota_usages.id']),
        sa.ForeignKeyConstraint(['allocated_id'],
                                ['quotas.id']),
        sa.PrimaryKeyConstraint('id'),
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
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('fingerprint', sa.String(255)),
        sa.Column('public_key', sa.Text()),
        sa.Column('type', sa.Enum('ssh', 'x509'), nullable=False,
                  default='ssh'),
        sa.UniqueConstraint('user_id', 'name',
                            name="uniq_key_pairs0user_id0name"),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
