.. -*- rst -*-

===========
 Instances
===========

Lists, creates, shows details for, updates, and deletes instances.

Create Instance
===============

.. rest_method:: POST /instances

Creates a instance.

The progress of this operation depends on the location of the
requested image, network I/O, selected type, and other factors.

The ``Location`` header returns the full URL to the newly created
instance and is available as a ``self`` and ``bookmark`` link in the
instance representation.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

  - name: instance_name
  - description: instance_description
  - instance_type_uuid: typeRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - networks: networks
  - networks.uuid: network_uuid
  - networks.port_type: network_port_type

**Example Create Instance: JSON request**

.. literalinclude:: ../../doc/api_samples/instances/instance-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - name: instance_name
  - description: instance_description
  - instance_type_uuid: typeRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - network_info: network_info
  - links: links
  - uuid: instance_uuid
  - status: instance_status
  - power_state: instance_power_state
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at

**Example Create Instance: JSON response**

.. literalinclude:: ../../doc/api_samples/instances/instance-create-resp.json
   :language: javascript
