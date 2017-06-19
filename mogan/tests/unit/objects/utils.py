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
"""Mogan object test utilities."""
import six

from mogan.common import exception
from mogan.common.i18n import _
from mogan import objects
from mogan.tests.unit.db import utils as db_utils


def check_keyword_arguments(func):
    @six.wraps(func)
    def wrapper(**kw):
        obj_type = kw.pop('object_type')
        result = func(**kw)

        extra_args = set(kw) - set(result)
        if extra_args:
            raise exception.InvalidParameterValue(
                _("Unknown keyword arguments (%(extra)s) were passed "
                  "while creating a test %(object_type)s object.") %
                {"extra": ", ".join(extra_args),
                 "object_type": obj_type})

        return result

    return wrapper


def get_test_server(ctxt, **kw):
    """Return a Server object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    kw['object_type'] = 'server'
    get_db_server_checked = check_keyword_arguments(
        db_utils.get_test_server)
    db_server = get_db_server_checked(**kw)

    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_server['id']
    server = objects.Server(ctxt, **db_server)
    return server


def create_test_server(ctxt, **kw):
    """Create and return a test server object.

    Create a server in the DB and return a Server object with appropriate
    attributes.
    """
    server = get_test_server(ctxt, **kw)
    server.create()
    return server


def get_test_server_fault(**kw):
    return {
        'id': kw.get('id', 123456),
        'server_uuid': kw.get('server_uuid'),
        'code': kw.get('code', 404),
        'message': kw.get('message', 'message'),
        'detail': kw.get('detail', 'detail'),
        'created_at': kw.get('create_at', None),
        'updated_at': kw.get('update_at', None)
    }


def get_test_server_faults(**kw):
    return {
        'fake-uuid': [
            {'id': 1, 'server_uuid': kw.get('server_uuid'), 'code': 123,
             'message': 'msg1', 'detail': 'detail', 'created_at': None,
             'updated_at': None},
            {'id': 2, 'server_uuid': kw.get('server_uuid'), 'code': 456,
             'message': 'msg2', 'detail': 'detail', 'created_at': None,
             'updated_at': None},
        ]
    }


def get_test_compute_node(ctxt, **kw):
    """Return a ComputeNode object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    kw['object_type'] = 'compute_node'
    get_db_compute_node_checked = check_keyword_arguments(
        db_utils.get_test_compute_node)
    db_node = get_db_compute_node_checked(**kw)

    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_node['id']
    node = objects.ComputeNode(ctxt)
    for key in db_node:
        if key != 'ports':
            setattr(node, key, db_node[key])
    return node


def create_test_compute_node(ctxt, **kw):
    """Create and return a test compute node object.

    Create a compute node in the DB and return a ComputeNode object with
    appropriate attributes.
    """
    node = get_test_compute_node(ctxt, **kw)
    node.create()
    return node


def get_test_compute_port(ctxt, **kw):
    """Return a ComputePort object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    kw['object_type'] = 'compute_port'
    get_db_compute_port_checked = check_keyword_arguments(
        db_utils.get_test_compute_port)
    db_port = get_db_compute_port_checked(**kw)

    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_port['id']
    port = objects.ComputePort(ctxt, **db_port)
    return port


def create_test_compute_port(ctxt, **kw):
    """Create and return a test compute port object.

    Create a compute port in the DB and return a ComputePort object with
    appropriate attributes.
    """
    port = get_test_compute_port(ctxt, **kw)
    port.create()
    return port
