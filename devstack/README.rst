====================
Enabling in Devstack
====================

1. Download DevStack::

    git clone https://git.openstack.org/openstack-dev/devstack.git
    cd devstack

2. Add this repo as an external repository::

     > cat local.conf
     [[local|localrc]]
     enable_plugin mogan https://git.openstack.org/openstack/mogan

3. run ``stack.sh``
