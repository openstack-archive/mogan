====================
Enabling in Devstack
====================

1. Download DevStack::

    git clone https://github.com/openstack-dev/devstack.git
    cd devstack

2. Add this repo as an external repository::

     > cat local.conf
     [[local|localrc]]
     enable_plugin nimble https://github.com/openstack/nimble

3. run ``stack.sh``
