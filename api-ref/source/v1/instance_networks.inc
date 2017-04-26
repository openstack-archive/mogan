.. -*- rst -*-

===================
 Instance Networks
===================

Instances Networks can be managed through networks sub-resource.

A Instance can be associated or dissociated with a floating IP by requesting
the floatingip sub-resource.


Instance Network Summary
========================

.. rest_method:: GET /v1/instances/{instance_uuid}/networks

Get a summary of the Instance's networks.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - ports: network_info

**Example instance network:**

.. literalinclude:: samples/instance_networks/instance-get-network-response.json


Add (Associate) Floating IP
===========================

.. rest_method:: POST /v1/instances/{instance_uuid}/networks/floatingips

Adds a floating IP address to an instance, which associates
that address with the instance.

If an instance is connected to multiple networks, you can associate a
floating IP address with a specific fixed IP address by using the
optional ``fixed_address`` parameter.

Normal response code: 204

Error codes: 400,401,403,404,409

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - address: address
    - fixed_address: fixed_address

**Example request to Add (Associate) Floating IP to an instance:**

.. literalinclude:: samples/instance_networks/instance-associate-fip-req.json

Response
--------

If successful, this method does not return content in the response body.


Remove (Disassociate) Floating IP
=================================

.. rest_method:: DELETE /v1/instances/{instance_uuid}/networks/floatingips/{fip_address}

Removes, or disassociates, a floating IP address from an instance.

Normal response codes: 204

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
itemNotFound(404), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - fip_address: address_path

Response
--------

If successful, this method does not return content in the response body.



Detach a network interface.
=================================

.. rest_method:: DELETE /v1/instances/{instance_uuid}/networks/interfaces/{port_id}

Detach a network interface from an instance.

Normal response codes: 204

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
itemNotFound(404), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident
    - port_id: port_ident

Response
--------

If successful, this method does not return content in the response body.
