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

"""Tests for manipulating Instance Faults via the DB API"""

from oslo_utils import uuidutils

from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbInstanceFaultTestCase(base.DbTestCase):
    def setUp(self):
        super(DbInstanceFaultTestCase, self).setUp()
        self.ctxt = {}

    def test_create_instance_fault(self):
        uuid = uuidutils.generate_uuid()
        # Ensure no faults registered for this instance
        faults = self.dbapi.instance_fault_get_by_instance_uuids(self.ctxt,
                                                                 [uuid])
        self.assertEqual(0, len(faults[uuid]))

        # Create a fault
        fault_values = utils.get_test_instance_fault(instance_uuid=uuid)
        fault = utils.create_test_instance_fault(self.ctxt, instance_uuid=uuid)

        ignored_keys = ['created_at', 'updated_at', 'id']
        self._assertEqualObjects(fault_values, fault, ignored_keys)

        # Retrieve the fault to ensure it was successfully added
        faults = self.dbapi.instance_fault_get_by_instance_uuids(self.ctxt,
                                                                 [uuid])
        self.assertEqual(1, len(faults[uuid]))
        self._assertEqualObjects(fault, faults[uuid][0])

    def test_get_instance_fault_by_instance(self):
        """Ensure we can retrieve faults for instance."""
        uuids = [uuidutils.generate_uuid(), uuidutils.generate_uuid()]
        fault_codes = [404, 500]
        expected = {}

        # Create faults
        for uuid in uuids:
            utils.create_test_instance(self.ctxt, instance_uuid=uuid)

            expected[uuid] = []
            for code in fault_codes:
                fault = utils.create_test_instance_fault(self.ctxt,
                                                         instance_uuid=uuid,
                                                         code=code)
                # We expect the faults to be returned ordered by created_at in
                # descending order, so insert the newly created fault at the
                # front of our list.
                expected[uuid].insert(0, fault)

        # Ensure faults are saved
        faults = self.dbapi.instance_fault_get_by_instance_uuids(self.ctxt,
                                                                 uuids)
        ignored_keys = ['created_at', 'updated_at', 'id']
        self.assertEqual(len(expected), len(faults))
        for uuid in uuids:
            self._assertEqualOrderedListOfObjects(expected[uuid],
                                                  faults[uuid],
                                                  ignored_keys)

    def test_delete_instance_faults_on_instance_destroy(self):
        instance = utils.create_test_instance(self.ctxt)
        fault = utils.create_test_instance_fault(self.ctxt,
                                                 instance_uuid=instance.uuid)
        faults = self.dbapi.instance_fault_get_by_instance_uuids(
            self.ctxt,
            [instance.uuid])
        self.assertEqual(1, len(faults[instance.uuid]))
        self._assertEqualObjects(fault, faults[instance.uuid][0])
        self.dbapi.instance_destroy(self.ctxt, instance.uuid)
        faults = self.dbapi.instance_fault_get_by_instance_uuids(
            self.ctxt,
            [instance.uuid])
        self.assertEqual(0, len(faults[instance.uuid]))
