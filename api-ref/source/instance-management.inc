.. -*- rst -*-

===============================
Instance Management (instances)
===============================

Instances can be managed through several sub-resources.

A Instance can be rebooted, turned on, or turned off by requesting a change to
its power state. This is handled asynchronously and tracked in the
``target_power_state`` field after the request is received.


Instance State Summary
======================

.. rest_method:: GET /v1/instances/{instance_ident}/states

Get a summary of the Instance's current power tatus.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_ident: instance_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - power_state: power_state
    - target_power_state: target_power_state

**Example instance state:**

.. literalinclude:: samples/instance-get-state-response.json


Change Instance Power State
===========================

.. rest_method:: PUT /v1/instances/{instance_ident}/states/power

Request a change to the Instance's power state.

Normal response code: 202

Error codes:
    - 409 (InstanceLocked, ClientError)
    - 400 (InvalidState)
    - 406 (NotAcceptable)
    - 503 (NoFreeConductorWorkers)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_ident: instance_ident
    - target: power_state

**Example request to power off a Instance:**

.. literalinclude:: samples/instance-set-power-off.json
