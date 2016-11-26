#
# Copyright 2016 Huawei Technologies Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""remove instance type projects

Revision ID: bbad1855a8d2
Revises: 91941bf1ebc9
Create Date: 2016-11-26 11:52:12.638000

"""

# revision identifiers, used by Alembic.
revision = 'bbad1855a8d2'
down_revision = '91941bf1ebc9'

from alembic import op


def upgrade():
    op.drop_table('instance_type_projects')
