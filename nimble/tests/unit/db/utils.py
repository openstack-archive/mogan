# Copyright 2016 Intel
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
"""Nimble test utilities."""


from nimble.db import api as db_api
from nimble.engine.baremetal import ironic_states as states


def get_test_instance(**kw):
    return {
        'id': kw.get('id', 123),
        'name': kw.get('name', None),
        'uuid': kw.get('uuid', '1be26c0b-03f2-4d2e-ae87-c02d7f33c123'),
        'description': kw.get('description', ''),
        'power_state': kw.get('power_state', states.NOSTATE),
        'status': kw.get('status', states.AVAILABLE),
        'task_state': kw.get('task_state', states.DEPLOYING),
        'instance_type_id': kw.get('instance_type_id', 1),
        'availability_zone': kw.get('availability_zone', ''),
        'image_uuid': kw.get('image_uuid', None),
        'network_uuid': kw.get('network_uuid', None),
        'node_uuid': kw.get('node_uuid', None),
        'extra': kw.get('extra', {}),
    }


def create_test_instance(**kw):
    """Create test instance entry in DB and return Instance DB object.

    Function to be used to create test Instance objects in the database.

    :param kw: kwargs with overriding values for instance's attributes.
    :returns: Test Instance DB object.

    """
    instance = get_test_instance(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del instance['id']
    dbapi = db_api.get_instance()
    return dbapi.create_instance(instance)
