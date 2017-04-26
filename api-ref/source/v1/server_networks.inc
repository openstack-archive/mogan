.. -*- rst -*-

===================
 Server Networks
===================

Servers Networks can be managed through networks sub-resource.

A Server can be associated or dissociated with a floating IP by requesting
the floatingip sub-resource.


Server Network Summary
========================

.. rest_method:: GET /v1/servers/{server_uuid}/networks

Get a summary of the Server's networks.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - ports: network_info

**Example server network:**

.. literalinclude:: samples/server_networks/server-get-network-response.json


Add (Associate) Floating IP
===========================

.. rest_method:: POST /v1/servers/{server_uuid}/networks/floatingips

Adds a floating IP address to a server, which associates
that address with the server.

If a server is connected to multiple networks, you can associate a
floating IP address with a specific fixed IP address by using the
optional ``fixed_address`` parameter.

Normal response code: 204

Error codes: 400,401,403,404,409

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - address: address
    - fixed_address: fixed_address

**Example request to Add (Associate) Floating IP to a server:**

.. literalinclude:: samples/server_networks/server-associate-fip-req.json

Response
--------

If successful, this method does not return content in the response body.


Remove (Disassociate) Floating IP
=================================

.. rest_method:: DELETE /v1/servers/{server_uuid}/networks/floatingips/{fip_address}

Removes, or disassociates, a floating IP address from a server.

Normal response codes: 204

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
itemNotFound(404), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - fip_address: address_path

Response
--------

If successful, this method does not return content in the response body.
