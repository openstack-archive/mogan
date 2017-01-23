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

.. literalinclude:: samples/instances/instance-get-network-response.json
