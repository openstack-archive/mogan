.. -*- rst -*-

=================
 Instance Lock
=================

Instances Lock can be managed through instances sub-resource.

An Instance can be lock, or unlock by requesting a change to
its lock state.


Change Instance Lock State
===========================

.. rest_method:: PUT /v1/instances/{instance_uuid}/lock

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

.. literalinclude:: samples/instances/lock-instance.json

**Example request to unlock an Instance:**

.. literalinclude:: samples/instances/unlock-instance.json
