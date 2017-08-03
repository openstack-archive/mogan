.. -*- rst -*-

=================
 Server States
=================

Servers States can be managed through states sub-resource.

A Server can be rebooted, turned on, or turned off by requesting a change to
its power state.


Server State Summary
======================

.. rest_method:: GET /v1/servers/{server_uuid}/states

Get a summary of the Server's current states.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - power_state: power_state
  - locked: lock_state
  - status: server_status

**Example server state:**

.. literalinclude:: samples/server_states/server-get-state-response.json


Change Server Power State
===========================

.. rest_method:: PUT /v1/servers/{server_uuid}/states/power

Request a change to the Server's power state.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (InvalidState)
    - 406 (NotAcceptable)

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - target: power_state_target

**Example request to power off a Server:**

.. literalinclude:: samples/server_states/server-set-power-off.json

Response
--------

If successful, this method does not return content in the response body.


Change Server Lock State
===========================

.. rest_method:: PUT /v1/servers/{server_uuid}/states/lock

Request a change to the Server's lockstate.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (BadRequest)
    - 403 (Forbidden)

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - target: lock_state

**Example request to lock a Server:**

.. literalinclude:: samples/server_states/lock-server.json

**Example request to unlock a Server:**

.. literalinclude:: samples/server_states/unlock-server.json

Response
--------

If successful, this method does not return content in the response body.


Change Server Provision State
===============================

.. rest_method:: PUT /v1/servers/{server_uuid}/states/provision

Request a change to the Server's provision state.

Normal response code: 202

Error codes:
    - 409 (ClientError)
    - 400 (BadRequest)
    - 403 (Forbidden)

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - target: provision_state
    - image_uuid: image_ident

**Example request to rebuild a Server:**

.. literalinclude:: samples/server_states/rebuild-server.json

Response
--------

If successful, this method does not return content in the response body.
