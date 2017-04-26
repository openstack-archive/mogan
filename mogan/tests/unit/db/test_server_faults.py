# Copyright 2017 Intel
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

"""Tests for manipulating Server Faults via the DB API"""

from oslo_utils import uuidutils

from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbServerFaultTestCase(base.DbTestCase):
    def setUp(self):
        super(DbServerFaultTestCase, self).setUp()
        self.ctxt = {}

    def test_create_server_fault(self):
        uuid = uuidutils.generate_uuid()
        # Ensure no faults registered for this server
        faults = self.dbapi.server_fault_get_by_server_uuids(self.ctxt,
                                                             [uuid])
        self.assertEqual(0, len(faults[uuid]))

        # Create a fault
        fault_values = utils.get_test_server_fault(server_uuid=uuid)
        fault = utils.create_test_server_fault(self.ctxt, server_uuid=uuid)

        ignored_keys = ['created_at', 'updated_at', 'id']
        self._assertEqualObjects(fault_values, fault, ignored_keys)

        # Retrieve the fault to ensure it was successfully added
        faults = self.dbapi.server_fault_get_by_server_uuids(self.ctxt,
                                                             [uuid])
        self.assertEqual(1, len(faults[uuid]))
        self._assertEqualObjects(fault, faults[uuid][0])

    def test_get_server_fault_by_server(self):
        """Ensure we can retrieve faults for server."""
        uuids = [uuidutils.generate_uuid(), uuidutils.generate_uuid()]
        fault_codes = [404, 500]
        expected = {}

        # Create faults
        for uuid in uuids:
            utils.create_test_server(self.ctxt, server_uuid=uuid)

            expected[uuid] = []
            for code in fault_codes:
                fault = utils.create_test_server_fault(self.ctxt,
                                                       server_uuid=uuid,
                                                       code=code)
                # We expect the faults to be returned ordered by created_at in
                # descending order, so insert the newly created fault at the
                # front of our list.
                expected[uuid].insert(0, fault)

        # Ensure faults are saved
        faults = self.dbapi.server_fault_get_by_server_uuids(self.ctxt,
                                                             uuids)
        ignored_keys = ['created_at', 'updated_at', 'id']
        self.assertEqual(len(expected), len(faults))
        for uuid in uuids:
            self._assertEqualOrderedListOfObjects(expected[uuid],
                                                  faults[uuid],
                                                  ignored_keys)

    def test_delete_server_faults_on_server_destroy(self):
        server = utils.create_test_server(self.ctxt)
        fault = utils.create_test_server_fault(self.ctxt,
                                               server_uuid=server.uuid)
        faults = self.dbapi.server_fault_get_by_server_uuids(
            self.ctxt,
            [server.uuid])
        self.assertEqual(1, len(faults[server.uuid]))
        self._assertEqualObjects(fault, faults[server.uuid][0])
        self.dbapi.server_destroy(self.ctxt, server.uuid)
        faults = self.dbapi.server_fault_get_by_server_uuids(
            self.ctxt,
            [server.uuid])
        self.assertEqual(0, len(faults[server.uuid]))
