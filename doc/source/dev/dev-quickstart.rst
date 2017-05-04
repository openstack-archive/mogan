.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Mogan.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

The gate currently runs the unit tests under Python 2.7, Python 3.4
and Python 3.5. It is strongly encouraged to run the unit tests locally prior
to submitting a patch.

.. note::
    Do not run unit tests on the same environment as devstack due to
    conflicting configuration with system dependencies.

.. note::
    This document is compatible with Python (3.5), Ubuntu (16.04) and Fedora (23).
    When referring to different versions of Python and OS distributions, this
    is explicitly stated.

.. seealso::

    http://docs.openstack.org/infra/manual/developers.html#development-workflow

Preparing Development System
============================

System Prerequisites
--------------------

The following packages cover the prerequisites for a local development
environment on most current distributions. Instructions for getting set up with
non-default versions of Python and on older distributions are included below as
well.

- Ubuntu/Debian::

    sudo apt-get install build-essential python-dev libssl-dev python-pip libmysqlclient-dev libxml2-dev libxslt-dev libpq-dev git git-review libffi-dev gettext ipmitool psmisc graphviz libjpeg-dev xinetd tftpd tftp

- Fedora 21/RHEL7/CentOS7::

    sudo yum install python-devel openssl-devel python-pip mysql-devel libxml2-devel libxslt-devel postgresql-devel git git-review libffi-devel gettext ipmitool psmisc graphviz gcc libjpeg-turbo-devel

  If using RHEL and yum reports "No package python-pip available" and "No
  package git-review available", use the EPEL software repository.
  Instructions can be found at `<https://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_.

- Fedora 22 or higher::

    sudo dnf install python-devel openssl-devel python-pip mysql-devel libxml2-devel libxslt-devel postgresql-devel git git-review libffi-devel gettext ipmitool psmisc graphviz gcc libjpeg-turbo-devel

  Additionally, if using Fedora 23, ``redhat-rpm-config`` package should be
  installed so that development virtualenv can be built successfully.

- openSUSE/SLE 12::

    sudo zypper install git git-review libffi-devel libmysqlclient-devel libopenssl-devel libxml2-devel libxslt-devel postgresql-devel python-devel python-nose python-pip gettext-runtime psmisc

  Graphviz is only needed for generating the state machine diagram. To install it
  on openSUSE or SLE 12, see
  `<https://software.opensuse.org/download.html?project=graphics&package=graphviz-plugins>`_.


(Optional) Installing Py34 requirements
---------------------------------------

If you need Python 3.4, follow the instructions above to install prerequisites
and *additionally* install the following packages:

- On Ubuntu 14.x/Debian::

    sudo apt-get install python3-dev

- On Ubuntu 16.04::

    wget https://www.python.org/ftp/python/3.4.4/Python-3.4.4.tgz
    sudo tar xzf Python-3.4.4.tgz
    cd Python-3.4.4
    sudo ./configure
    sudo make altinstall

    # This will install Python 3.4 without replacing 3.5. To check if 3.4 was installed properly
    run this command:

    python3.4 -V

- On Fedora 21/RHEL7/CentOS7::

    sudo yum install python3-devel

- On Fedora 22 and higher::

    sudo dnf install python3-devel

(Optional) Installing Py35 requirements
---------------------------------------

If you need Python 3.5 support on an older distro that does not already have
it, follow the instructions for installing prerequisites above and
*additionally* run the following commands.

- On Ubuntu 14.04::

    wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tgz
    sudo tar xzf Python-3.5.2.tgz
    cd Python-3.5.2
    sudo ./configure
    sudo make altinstall

    # This will install Python 3.5 without replacing 3.4. To check if 3.5 was installed properly
    run this command:

    python3.5 -V

- On Fedora 23::

    sudo dnf install -y dnf-plugins-core
    sudo dnf copr enable -y mstuchli/Python3.5
    dnf install -y python35-python3

Python Prerequisites
--------------------

If your distro has at least tox 1.8, use similar command to install
``python-tox`` package. Otherwise install this on all distros::

    sudo pip install -U tox

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv


Running Unit Tests Locally
==========================

If you haven't already, Mogan source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/mogan
    cd mogan

Running Unit and Style Tests
----------------------------

All unit tests should be run using tox. To run Mogan's entire test suite::

    # to run the py27, py34, py35 unit tests, and the style tests
    tox

To run a specific test or tests, use the "-e" option followed by the tox target
name. For example::

    # run the unit tests under py27 and also run the pep8 tests
    tox -epy27 -epep8

.. note::
    If tests are run under py27 and then run under py34 or py35 the following error may occur::

      db type could not be determined
      ERROR: InvocationError: '/home/ubuntu/mogan/.tox/py35/bin/ostestr'

    To overcome this error remove the file `.testrepository/times.dbm`
    and then run the py34 or py35 test.

You may pass options to the test programs using positional arguments.
To run a specific unit test, this passes the -r option and desired test
(regex string) to `os-testr <https://pypi.python.org/pypi/os-testr>`_::

    # run a specific test for Python 2.7
    tox -epy27 -- -r test_name

Debugging unit tests
--------------------

In order to break into the debugger from a unit test we need to insert
a breaking point to the code:

.. code-block:: python

  import pdb; pdb.set_trace()

Then run ``tox`` with the debug environment as one of the following::

  tox -e debug
  tox -e debug test_file_name
  tox -e debug test_file_name.TestClass
  tox -e debug test_file_name.TestClass.test_name

For more information see the `oslotest documentation
<http://docs.openstack.org/developer/oslotest/features.html#debugging-with-oslo-debug-helper>`_.

Additional Tox Targets
----------------------

There are several additional tox targets not included in the default list, such
as the target which builds the documentation site.   See the ``tox.ini`` file
for a complete listing of tox targets. These can be run directly by specifying
the target name::

    # generate the documentation pages locally
    tox -edocs

    # generate the sample configuration file
    tox -egenconfig


Deploying Mogan with DevStack
=============================

DevStack may be configured to deploy Mogan, It is easy to develop Mogan
with the devstack environment. Mogan depends on Ironic, Neutron, and Glance
to create and schedule virtual machines to simulate bare metal servers.
It is highly recommended to deploy on an expendable virtual machine and not
on your personal work station. Deploying Mogan with DevStack requires a
machine running Ubuntu 14.04 (or later) or Fedora 20 (or later). Make sure
your machine is fully up to date and has the latest packages installed before
beginning this process.

.. seealso::

    http://docs.openstack.org/developer/devstack/


Devstack will no longer create the user 'stack' with the desired
permissions, but does provide a script to perform the task::

    git clone https://git.openstack.org/openstack-dev/devstack.git devstack
    sudo ./devstack/tools/create-stack-user.sh

Switch to the stack user and clone DevStack::

    sudo su - stack
    git clone https://git.openstack.org/openstack-dev/devstack.git devstack

Create devstack/local.conf with minimal settings required to enable Mogan

.. note::
    As Ironic tempest configuration depends on baremetal flavor, we have to
    temporarily disable tempest in the devstack config file to make it work
    with Ironic.
    It's ok to enable Horizon, Nova and Cinder services, they don't impact
    Mogan at all, disable them in the demo configuration to only deploy the
    dependent services

::

    cd devstack
    cat >local.conf <<END
    [[local|localrc]]
    # Credentials
    ADMIN_PASSWORD=password
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password
    SWIFT_HASH=password
    SWIFT_TEMPURL_KEY=password

    # Enable Ironic plugin
    enable_plugin ironic git://git.openstack.org/openstack/ironic

    # Enable Mogan plugin
    enable_plugin mogan git://git.openstack.org/openstack/mogan

    # Enable Neutron which is required by Ironic and disable nova-network.
    disable_service n-net
    enable_service q-svc
    enable_service q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service neutron

    # Enable Swift for agent_* drivers
    enable_service s-proxy
    enable_service s-object
    enable_service s-container
    enable_service s-account

    # Disable Horizon
    disable_service Horizon
    # Disable Cinder
    disable_service cinder c-sch c-api c-vol
    # Disable Tempest
    disable_service tempest

    # Swift temp URL's are required for agent_* drivers.
    SWIFT_ENABLE_TEMPURLS=True

    # Create 3 virtual machines to pose as Ironic's baremetal nodes.
    IRONIC_VM_COUNT=3
    IRONIC_VM_SSH_PORT=22
    IRONIC_BAREMETAL_BASIC_OPS=True

    # Enable Ironic drivers.
    IRONIC_ENABLED_DRIVERS=fake,agent_ssh,agent_ipmitool,pxe_ssh,pxe_ipmitool

    # Change this to alter the default driver for nodes created by devstack.
    # This driver should be in the enabled list above.
    IRONIC_DEPLOY_DRIVER=agent_ipmitool

    # Using Ironic agent deploy driver by default, so don't use whole disk
    # image in tempest.
    IRONIC_TEMPEST_WHOLE_DISK_IMAGE=False

    # The parameters below represent the minimum possible values to create
    # functional nodes.
    IRONIC_VM_SPECS_RAM=1280
    IRONIC_VM_SPECS_DISK=10

    # To build your own IPA ramdisk from source, set this to True
    IRONIC_BUILD_DEPLOY_RAMDISK=False

    # Log all output to files
    LOGFILE=$HOME/devstack.log
    LOGDIR=$HOME/logs
    IRONIC_VM_LOG_DIR=$HOME/ironic-bm-logs

    END

.. note::
    If you want to enable shellinabox console functionality, please disable
    VM console log and set the ironic deployment driver as *agent_ssh* in
    the devstack config file::

    IRONIC_VM_LOG_CONSOLE=False
    IRONIC_DEPLOY_DRIVER=agent_ssh

.. note::
    Git protocol requires access to port 9418, which is not a standard port that
    corporate firewalls always allow. If you are behind a firewall or on a proxy that
    blocks Git protocol, modify the ``enable_plugin`` line to use ``https://`` instead
    of ``git://`` and add ``GIT_BASE=https://git.openstack.org`` to the credentials::

      GIT_BASE=https://git.openstack.org

      # Enable Mogan plugin
      enable_plugin mogan https://git.openstack.org/openstack/mogan

Run stack.sh::

    ./stack.sh

Source credentials, and spawn a server as the ``demo`` user::

    source ~/devstack/openrc

    # query the image id of the default cirros image
    image=$(openstack image show $DEFAULT_IMAGE_NAME -f value -c id)

    # spawn server
    As our moganclient is not ready now, will add this soon...

Building developer documentation
================================

If you would like to build the documentation locally, eg. to test your
documentation changes before uploading them for review, run these
commands to build the documentation set:

- On your local machine::

    # activate your development virtualenv
    source .tox/venv/bin/activate

    # build the docs
    tox -edocs

    #Now use your browser to open the top-level index.html located at:
    mogan/doc/build/html/index.html


- On a remote machine::

    # Go to the directory that contains the docs
    cd ~/mogan/doc/source/

    # Build the docs
    tox -edocs

    # Change directory to the newly built HTML files
    cd ~/mogan/doc/build/html/

    # Create a server using python on port 8000
    python -m SimpleHTTPServer 8000

    #Now use your browser to open the top-level index.html located at:
    http://host_ip:8000
