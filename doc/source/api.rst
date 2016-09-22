=====================
Instance API Overview
=====================

List, Searching, Creating, Updating, and Deleting of Instance resources are done
through the `/instances` resource. There are also several sub-resources, which
allow further actions to be performed on an Instance.

Instances
---------

List Instances::

  GET /instances

List Instances Detailed::

  GET /instances/detail

Show Instance Details::

  GET /instances/{instance_ident}

Create Instance::

  POST /instances

Update Instance::

  PATCH /instances/{instance_ident}

Delete Instance::

  DELETE /instances/{instance_ident}


Instance Management
-------------------

Instances can be managed through several sub-resources

Instance State Summary::

  GET /instances/{instance_ident}/states

Change Instance Power State(on, off, reboot)::

  PUT /instances/{instance_ident}/states/power

Change Instance Provision State(rebuild)::

  PUT /instances/{instance_ident}/states/provision

Get Console::

  GET /instances/{instance_ident}/states/console

Show Console Output::

  GET /instances/{instance_ident}/states/consoleoutput
