.. -*- rst -*-

===================
 Manageable Servers
===================

Lists, manages manageable servers.

List manageable servers information
===================================

.. rest_method:: GET /manageable_servers

Lists manageable servers information.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Response
--------

.. rest_parameters:: parameters.yaml

  - manageable_servers: manageable_servers
  - uuid: manageable_servers_uuid
  - name: manageable_servers_name
  - resource_class: manageable_servers_resource_class
  - power_state: manageable_servers_power_state
  - provision_state: manageable_servers_provision_state
  - ports: manageable_servers_ports
  - portgroups: manageable_servers_portgroups
  - image_source: manageable_servers_image_source

**Example List manageable servers information**

.. literalinclude:: samples/manageable_servers/manageable-servers-list-resp.json
   :language: javascript

Manage an existing server
=========================

.. rest_method:: POST /manageable_servers

Manage a server.

Manage nodes in active which migrated by operators.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - node_uuid: manageable_servers_uuid
  - metadata: metadata

**Example Manage Server: JSON request**

.. literalinclude:: samples/manageable_servers/server-manage-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - addresses: addresses
  - links: links
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at
  - launched_at: launched_at
  - metadata: metadata
  - affinity_zone: affinity_zone
  - key_name: key_name
  - node_uuid: manageable_servers_uuid
  - partitions: partitions

**Example Manage Server: JSON response**

.. literalinclude:: samples/manageable_servers/server-manage-resp.json
   :language: javascript
