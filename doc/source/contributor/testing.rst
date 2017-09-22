..
      Copyright (c) 2017 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=================
Running the Tests
=================

Mogan includes an extensive set of automated unit tests which are
run through tox_.

Install tox
-----------

Install ``tox`` using pip::

   $ sudo pip install tox

Python Guideline Enforcement
----------------------------

All code has to pass the pep8 style guideline to merge into OpenStack, to
validate the code against these guidelines you can run::

    $ tox -e pep8

Unit Testing
------------

It is strongly encouraged to run the unit tests locally under one or more
test environments prior to submitting a patch. To run all the recommended
environments sequentially and pep8 style guideline run::

    $ tox

You can also selectively pick specific test environments by listing your
chosen environments after a -e flag::

    $ tox -e py35,py27,pep8,pypy

As tox is a wrapper around testr, it also accepts the same flags as testr.
See the `testr documentation`_ for details about these additional flags.

.. _testr documentation: https://testrepository.readthedocs.org/en/latest/MANUAL.html

Use a double hyphen to pass options to testr. For example, to run only tests
under tests/unit/api/::

    $ tox -e py27 -- mogan.tests.unit.api

.. note::
  Tox sets up virtual environment and installs all necessary dependencies.
  Sharing the environment with devstack testing is not recommended due to
  conflicting configuration with system dependencies.

Debug tests
-----------
To debug tests (ie. break into pdb debugger), you can use ''debug'' tox
environment. Here's an example, passing the name of a test since you'll
normally only want to run the test that hits your breakpoint::

    $ tox -e debug mogan.tests.unit.cmd.test_dbsync.DbSyncTestCase

For reference, the ``debug`` tox environment implements the instructions
here: https://wiki.openstack.org/wiki/Testr#Debugging_.28pdb.29_Tests

Functional tests
----------------
To run functional tests, you can specify the *functional* as test environment::

    $ tox -e functional

Tempest tests
-------------
Tempest is a set of integration tests to be run against a live OpenStack
environment, to run tempest of mogan part, you need to enable tempest
installed and configured correctly. In devstack installation, you need to
enable tempest and mogan in `local.conf` and run `stack.sh`. Then you can
run mogan tempest tests with `tempest run` command, see::

   $ ./stack.sh
   $ cd /opt/stack/tempest/
   $ tempest run -t --regex "^mogan\."

For more details, you can see `tempest documentation`_

.. _tempest documentation: https://docs.openstack.org/tempest/latest/

.. seealso::

   * tox_

.. _tox: https://tox.readthedocs.io/en/latest/
