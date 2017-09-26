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

"""add server tags

Revision ID: cf73c09d3ff2
Revises: 0de89f877016
Create Date: 2017-09-21 04:11:09.636891

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cf73c09d3ff2'
down_revision = '91941bf1ebc9'


def upgrade():
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
