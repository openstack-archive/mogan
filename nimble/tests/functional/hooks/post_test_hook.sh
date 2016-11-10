#!/bin/bash -xe

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside post_test_hook function in devstack gate.

function generate_testr_results {
    if [ -f .testrepository/0 ]; then
        sudo .tox/functional/bin/testr last --subunit > $WORKSPACE/testrepository.subunit
        sudo mv $WORKSPACE/testrepository.subunit $BASE/logs/testrepository.subunit
        sudo /usr/os-testr-env/bin/subunit2html $BASE/logs/testrepository.subunit $BASE/logs/testr_results.html
        sudo gzip -9 $BASE/logs/testrepository.subunit
        sudo gzip -9 $BASE/logs/testr_results.html
        sudo chown jenkins:jenkins $BASE/logs/testrepository.subunit.gz $BASE/logs/testr_results.html.gz
        sudo chmod a+r $BASE/logs/testrepository.subunit.gz $BASE/logs/testr_results.html.gz
    fi
}

export NIMBLE_DIR="$BASE/new/nimble"

# Go to the nimble dir
cd $NIMBLE_DIR

if [[ -z "$STACK_USER" ]]; then
    export STACK_USER=stack
fi

sudo chown -R $STACK_USER:stack $NIMBLE_DIR

# If we're running in the gate find our keystone endpoint to give to
# gabbi tests and do a chown. Otherwise the existing environment
# should provide URL and TOKEN.
if [ -d $BASE/new/devstack ]; then
    source $BASE/new/devstack/openrc admin admin
    if [ $OS_IDENTITY_API_VERSION == '2.0' ]; then
        urltag='publicURL'
    else
        urltag='public'
    fi
    openstack catalog list
    export NIMBLE_SERVICE_URL=$(openstack catalog show baremetal_compute -c endpoints -f value | awk "/$urltag"'/{print $2}')
    export NIMBLE_SERVICE_TOKEN=$(openstack token issue -c id -f value)
    export NIMBLE_IMAGE_REF=$(openstack image list --limit 1 -c ID -f value)
fi

# Run tests
echo "Running nimble functional test suite"
set +e

sudo -E -H -u ${STACK_USER:-${USER}} tox -efunctional
EXIT_CODE=$?
set -e

# Collect and parse result
generate_testr_results
exit $EXIT_CODE
