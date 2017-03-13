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


def get_test_instance(**kw):
    fake_instance_nics = [{
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
        'port_type': 'test_type',
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
        'instance_type_uuid': kw.get('instance_type_uuid',
                                     '28708dff-283c-449e-9bfa-a48c93480c86'),
        'availability_zone': kw.get('availability_zone', 'test_az'),
        'image_uuid': kw.get('image_uuid',
                             'ac3b2291-b9ef-45f6-8eeb-21ac568a64a5'),
        'nics': kw.get('nics', fake_instance_nics),
        'node_uuid': kw.get('node_uuid',
                            'f978ef48-d4af-4dad-beec-e6174309bc71'),
        'launched_at': kw.get('launched_at'),
        'deleted_at': kw.get('deleted_at'),
        'extra': kw.get('extra', {}),
        'deleted': kw.get('deleted', False),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
        'locked': kw.get('locked', False),
        'locked_by': kw.get('locked_by', None),
    }


def create_test_instance(context={}, **kw):
    """Create test instance entry in DB and return Instance DB object.

    Function to be used to create test Instance objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for instance's attributes.
    :returns: Test Instance DB object.

    """
    instance = get_test_instance(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del instance['id']
    dbapi = db_api.get_instance()

    return dbapi.instance_create(context, instance)


def get_test_compute_node(**kw):
    return {
        'id': kw.get('id', 123),
        'cpus': kw.get('cpus', 16),
        'memory_mb': kw.get('memory_mb', 10240),
        'hypervisor_type': kw.get('hypervisor_type', 'ironic'),
        'availability_zone': kw.get('availability_zone', 'test_az'),
        'node_uuid': kw.get('node_uuid',
                            'f978ef48-d4af-4dad-beec-e6174309bc71'),
        'capabilities': kw.get('capabilities', {}),
        'extra': kw.get('extra', {}),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
    }


def create_test_compute_node(context={}, **kw):
    """Create test compute node entry in DB and return ComputeNode DB object.

    Function to be used to create test ComputeNode objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for node's attributes.
    :returns: Test ComputeNode DB object.

    """
    node = get_test_compute_node(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del node['id']
    dbapi = db_api.get_instance()

    return dbapi.compute_node_create(context, node)


def get_test_compute_port(**kw):
    return {
        'id': kw.get('id', 123),
        'port_type': kw.get('port_type', '1GE'),
        'port_uuid': kw.get('port_uuid',
                            'f978ef48-d4af-4dad-beec-e6174309bc72'),
        'node_uuid': kw.get('node_uuid',
                            'f978ef48-d4af-4dad-beec-e6174309bc71'),
        'extra': kw.get('extra', {}),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
    }


def create_test_compute_port(context={}, **kw):
    """Create test compute port entry in DB and return ComputePort DB object.

    Function to be used to create test ComputePort objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for port's attributes.
    :returns: Test ComputePort DB object.

    """
    port = get_test_compute_port(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del port['id']
    dbapi = db_api.get_instance()

    return dbapi.compute_port_create(context, port)


def get_test_instance_type(**kw):
    return {
        'uuid': kw.get('uuid', uuidutils.generate_uuid()),
        'name': kw.get('name', 'test'),
        'description': kw.get('description', 'test'),
        'is_public': kw.get('is_public', 1),
        'updated_at': kw.get('updated_at'),
        'created_at': kw.get('created_at'),
    }


def create_test_instance_type(context={}, **kw):
    """Create test instance type entry in DB and return the DB object.

    Function to be used to create test Instance Type objects in the database.

    :param context: The request context, for access checks.
    :param kw: kwargs with overriding values for instance type's attributes.
    :returns: Test Instance Type DB object.

    """
    instance_type = get_test_instance_type(**kw)
    dbapi = db_api.get_instance()

    return dbapi.instance_type_create(context, instance_type)


def get_test_quota(**kw):
    return {
        'id': kw.get('id', 123),
        'resource_name': kw.get('resource_name', 'instances'),
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
    :param kw: kwargs with overriding values for instance's attributes.
    :returns: Test Quota DB object.

    """
    quota = get_test_quota(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del quota['id']
    dbapi = db_api.get_instance()

    return dbapi.quota_create(context, quota)
