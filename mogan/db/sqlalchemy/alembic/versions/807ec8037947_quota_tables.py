# Copyright 2017 FiberHome Telecommunication Technologies CO.,LTD
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

"""quota tables

Revision ID: 807ec8037947
Revises: 91941bf1ebc9
Create Date: 2017-02-08 22:13:09.021005

"""

# revision identifiers, used by Alembic.
revision = '807ec8037947'
down_revision = '91941bf1ebc9'

from alembic import op
import sqlalchemy as sa


def upgrade():
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
                            name='uniq_quotas0resource_name'),
        mysql_ENGINE='InnoDB',
        mysql_DEFAULT_CHARSET='UTF8'
    )
    op.create_table(
        'reservations',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('usage_id', sa.Integer(), nullable=False),
        sa.Column('allocated_id', sa.Integer(), nullable=False),
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
