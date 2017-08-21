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
"""Mogan test utilities."""

from oslo_utils import uuidutils

from mogan.common import states
from mogan.db import api as db_api


def get_test_server(**kw):
    fake_server_nics = [{
        'port_id': uuidutils.generate_uuid(),
        'network_id': 'bf942f63-c284-4eb8-925b-c2fa1a89ed33',
        'mac_address': '52:54:00:6a:b7:cc',
        'fixed_ips': [
            {
                "subnet_id": "3aa1202b-9269-4c51-8eb3-cfac689fadda",
                "ip_address": "11.1.0.11"
            },
            {
                "subnet_id": "56a2438f-877b-423f-ab7b-166c1aeafdde",
                "ip_address": "2001:db8:8000:0:5054:ff:fe6a:b7cc"
            }
        ],
        'floating_ip': '',
    }, ]

    return {
        'id': kw.get('id', 123),
        'uuid': kw.get('uuid', uuidutils.generate_uuid()),
        'name': kw.get('name', 'test'),
        'description': kw.get('description', 'test'),
        'project_id': kw.get('project_id',
                             'c18e8a1a870d4c08a0b51ced6e0b6459'),
        'user_id': kw.get('user_id', 'cdbf77d47f1d4d04ad9b7ff62b672467'),
        'status': kw.get('status', states.ACTIVE),
        'power_state': kw.get('power_state', 'power on'),
        'flavor_uuid': kw.get('flavor_uuid',
                              '28708dff-283c-449e-9bfa-a48c93480c86'),
        'availability_zone': kw.get('availability_zone', 'test_az'),
        'image_uuid': kw.get('image_uuid',
                             'ac3b2291-b9ef-45f6-8eeb-21ac568a64a5'),
        'nics': kw.get('nics', fake_server_nics),
        'node_uuid': kw.get('node_uuid',
                            'f978ef48-d4af-4dad-beec-e6174309bc71'),
        'launched_at': kw.get('launched_at'),
        'extra': kw.get('extra', {}),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
        'locked': kw.get('locked', False),
        'locked_by': kw.get('locked_by', None),
        'affinity_zone': 'ZON1',
    }


def create_test_server(context={}, **kw):
    """Create test server entry in DB and return Server DB object.

    Function to be used to create test Server objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for server's attributes.
    :returns: Test Server DB object.

    """
    server = get_test_server(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del server['id']
    dbapi = db_api.get_instance()

    return dbapi.server_create(context, server)


def get_test_flavor(**kw):
    return {
        'id': kw.get('id', 123),
        'uuid': kw.get('uuid', uuidutils.generate_uuid()),
        'name': kw.get('name', 'test'),
        'description': kw.get('description', 'test'),
        'resources': kw.get('resources', {}),
        'resource_traits': kw.get('resource_traits', {}),
        'resource_aggregates': kw.get('resource_aggregates', {}),
        'is_public': kw.get('is_public', 1),
        'disabled': kw.get('disabled', 0),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
    }


def create_test_flavor(context={}, **kw):
    """Create test server type entry in DB and return the DB object.

    Function to be used to create test Flavor objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for server type's attributes.
    :returns: Test Flavor DB object.

    """
    flavor = get_test_flavor(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del flavor['id']
    dbapi = db_api.get_instance()

    return dbapi.flavor_create(context, flavor)


def get_test_server_fault(**kw):
    return {
        'server_uuid': kw.get('server_uuid'),
        'code': kw.get('code', 404),
        'message': kw.get('message', 'message'),
        'detail': kw.get('detail', 'detail'),
        'created_at': kw.get('create_at', None),
        'updated_at': kw.get('update_at', None)
    }


def create_test_server_fault(context={}, **kw):
    """Create test server fault entry in DB and return the DB object.

    Function to be used to create test Server Fault objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for server fault's attributes.
    :returns: Test Server Fault DB object.

    """
    server_fault = get_test_server_fault(**kw)
    dbapi = db_api.get_instance()

    return dbapi.server_fault_create(context, server_fault)


def get_test_quota(**kw):
    return {
        'id': kw.get('id', 123),
        'resource_name': kw.get('resource_name', 'servers'),
        'project_id': kw.get('project_id',
                             'c18e8a1a870d4c08a0b51ced6e0b6459'),
        'hard_limit': kw.get('hard_limit', 10),
        'allocated': kw.get('allocated', 0),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_quota(context={}, **kw):
    """Create test quota entry in DB and return quota DB object.

    Function to be used to create test Quota objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for server's attributes.
    :returns: Test Quota DB object.

    """
    quota = get_test_quota(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del quota['id']
    dbapi = db_api.get_instance()

    return dbapi.quota_create(context, quota)


def get_test_aggregate(**kw):
    return {
        'id': kw.get('id', 123),
        'uuid': kw.get('uuid', uuidutils.generate_uuid()),
        'name': kw.get('name', 'test'),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
    }


def create_test_aggregate(context={}, **kw):
    """Create test aggregate entry in DB and return the DB object.

    Function to be used to create test Aggregate objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for aggregate's attributes.
    :returns: Test Aggregate DB object.

    """
    agg = get_test_aggregate(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del agg['id']
    dbapi = db_api.get_instance()

    return dbapi.aggregate_create(context, agg)


def get_test_server_group(**kw):
    return {
        'id': kw.get('id', 123),
        'name': kw.get('name', 'test'),
        'uuid': kw.get('uuid', uuidutils.generate_uuid()),
        'user_id': kw.get('user_id', '2b846ce623754aa1b2ae3f99ff297cb8'),
        'project_id': kw.get('project_id', '9851baf53c75452dad7951bca7b3dbac'),
        'policies': kw.get('policies', ["anti-affinity", "affinity"]),
        'members': kw.get('members', ['server1', 'server2']),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('updated_at')
    }


def create_test_server_group(context={}, **kw):
    """Create test server fault entry in DB and return the DB object.

    Function to be used to create test Server Fault objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for server fault's attributes.
    :returns: Test Server Fault DB object.

    """
    server_fault = get_test_server_group(**kw)
    dbapi = db_api.get_instance()
    members = server_fault.pop('members')
    policies = server_fault.pop('policies')
    return dbapi.server_group_create(context, server_fault, policies=policies,
                                     members=members)
