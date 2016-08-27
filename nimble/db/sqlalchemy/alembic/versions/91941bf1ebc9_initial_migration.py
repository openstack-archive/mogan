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
        'instance_types',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uniq_instance_types0name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'instance_type_projects',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_type_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['instance_type_id'], ['instance_types.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'instances',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('power_state', sa.String(length=255), nullable=True),
        sa.Column('task_state', sa.String(length=255), nullable=True),
        sa.Column('instance_type_id', sa.Integer(), nullable=True),
        sa.Column('image_uuid', sa.String(length=36), nullable=True),
        sa.Column('network_uuid', sa.String(length=36), nullable=True),
        sa.Column('launched_at', sa.DateTime(), nullable=True),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),
        sa.Column('availability_zone', sa.String(length=255), nullable=True),
        sa.Column('node_uuid', sa.String(length=36), nullable=True),
        sa.Column('extra', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_instances0uuid'),
        sa.UniqueConstraint('name', name='uniq_instances0name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'nodes',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('instance_uuid', sa.String(length=36), nullable=True),
        sa.Column('instance_type_id', sa.Integer(), nullable=True),
        sa.Column('availability_zone', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
