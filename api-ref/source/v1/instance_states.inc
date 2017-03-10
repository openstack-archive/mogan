.. -*- rst -*-

=================
 Instance States
=================

Instances States can be managed through states sub-resource.

A Instance can be rebooted, turned on, or turned off by requesting a change to
its power state.


Instance State Summary
======================

.. rest_method:: GET /v1/instances/{instance_uuid}/states

Get a summary of the Instance's current states.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - power_state: power_state
  - locked: lock_state
  - status: instance_status

**Example instance state:**

.. literalinclude:: samples/instance_states/instance-get-state-response.json


Change Instance Power State
===========================

.. rest_method:: PUT /v1/instances/{instance_uuid}/states/power

Request a change to the Instance's power state.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (InvalidState)
    - 406 (NotAcceptable)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - target: power_state_target

**Example request to power off a Instance:**

.. literalinclude:: samples/instance_states/instance-set-power-off.json

Response
--------

If successful, this method does not return content in the response body.


Change Instance Lock State
===========================

.. rest_method:: PUT /v1/instances/{instance_uuid}/states/lock

Request a change to the Instance's lockstate.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (BadRequest)
    - 403 (Forbidden)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - target: lock_state

**Example request to lock an Instance:**

.. literalinclude:: samples/instance_states/lock-instance.json

**Example request to unlock an Instance:**

.. literalinclude:: samples/instance_states/unlock-instance.json

Response
--------

If successful, this method does not return content in the response body.


Change Instance Provision State
===============================

.. rest_method:: PUT /v1/instances/{instance_uuid}/states/provision

Request a change to the Instance's provision state.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (BadRequest)
    - 403 (Forbidden)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - target: provision_state

**Example request to rebuild an Instance:**

.. literalinclude:: samples/instance_states/rebuild-instance.json

Response
--------

If successful, this method does not return content in the response body.
