#!/bin/bash
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

# This script is executed inside gate_hook function in devstack gate.

# TODO(liusheng): will enable ironic services if add more functional tests
ENABLED_SERVICES="key"

# The backend is passed in by the job as the first and only argument
export DEVSTACK_GATE_INSTALL_TESTONLY=1
export DEVSTACK_GATE_NO_SERVICES=1
export DEVSTACK_GATE_TEMPEST=0
export DEVSTACK_GATE_EXERCISES=0
export KEEP_LOCALRC=1

export ENABLED_SERVICES

$BASE/new/devstack-gate/devstack-vm-gate.sh
