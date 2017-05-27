.. -*- rst -*-

===========
 Servers
===========

Lists, creates, shows details for, updates, and deletes servers.

Create Server
===============

.. rest_method:: POST /servers

Creates a server.

The progress of this operation depends on the location of the
requested image, network I/O, selected type, and other factors.

The ``Location`` header returns the full URL to the newly created
server and is available as a ``self`` and ``bookmark`` link in the
server representation.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - networks: networks
  - networks.net_id: network_uuid
  - networks.port_type: network_port_type
  - user_data: user_data
  - personality: personality
  - key_name: key_name

**Example Create Server: JSON request**

.. literalinclude:: samples/servers/server-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - nics: nics
  - links: links
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at
  - extra: extra

**Example Create Server: JSON response**

.. literalinclude:: samples/servers/server-create-resp.json
   :language: javascript

Create Multiple Servers
=========================

.. rest_method:: POST /servers

Create Multiple Servers.

There is a second kind of create call which can create multiple servers
at once. This supports all the same parameters as create with a few additional
attributes specific to multiple create.

Error handling for multiple create is not as consistent as for single server
create, and there is no guarantee that all the servers will be created
successfully.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), conflict(409)

Request (Additional Parameters)
-------------------------------

These are the parameters beyond single create that are supported.

.. rest_parameters:: parameters.yaml

  - name: multi_server_name_body
  - min_count: min_count_body
  - max_count: max_count_body

**Example Create Multiple Server: JSON request**

.. literalinclude:: samples/servers/multi-server-create-req.json
   :language: javascript

Response
--------

The first server will be returned. The returned paramaters is same to creating
a single server's.

**Example Create Multiple Server: JSON response**

.. literalinclude:: samples/servers/server-create-resp.json
   :language: javascript


List Servers
===============

.. rest_method:: GET /servers

Return a list of bare metal Servers, with some useful information about each
Server.

By default, this query will return the name, server uuid, server status
and description for each Server.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401),
forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

  - all_tenants: all_tenants
  - fields: fields

Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - links: links

**Example List of Servers: JSON response**

.. literalinclude:: samples/servers/server-list-resp.json
   :language: javascript


List Servers Detailed
=======================

.. rest_method:: GET /servers/detail

Return a list of bare metal Servers with complete details. We can also apply
filters to show more precisely the servers.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401),
forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

  - server_uuid: server_uuid
  - name: server_name
  - status: server_status
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - floating_ip: address
  - all_tenants: all_tenants


Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - nics: nics
  - links: links
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at
  - launched_at: launched_at
  - extra: extra

**Example Detailed list of Servers: JSON response**

.. literalinclude:: samples/servers/server-list-detail-resp.json
   :language: javascript


Show Server Details
=====================

.. rest_method:: GET /servers/{server_uuid}

Shows details of a server. By default, this will return the full
representation of the resource; an optional fields parameter can be supplied to
return only the specified set.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - server_uuid: server_ident
  - fields: fields

Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - nics: nics
  - links: links
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - fault_info: server_fault
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at
  - launched_at: launched_at
  - extra: extra

**Example Server Details: JSON response**

.. literalinclude:: samples/servers/server-detail-resp.json
   :language: javascript

**Example Server Details With Fault: JSON response**

.. literalinclude:: samples/servers/server-detail-resp-when-error.json
   :language: javascript


Update Server
===============

.. rest_method:: PATCH /servers/{server_uuid}

Updates the infromation stored about a server.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), conflict(409)

Request
-------

The BODY of the PATCH request must be a JSON PATCH document, adhering to
`RFC 6902 <https://tools.ietf.org/html/rfc6902>`_.

.. rest_parameters:: parameters.yaml

  - server_uuid: server_ident

**Example Update Server: JSON request**

.. literalinclude:: samples/servers/server-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - name: server_name
  - description: server_description
  - flavor_uuid: flavorRef
  - image_uuid: imageRef
  - availability_zone: availability_zone
  - nics: nics
  - links: links
  - uuid: server_uuid
  - status: server_status
  - power_state: server_power_state
  - project_id: project_id_body
  - user_id: user_id_body
  - updated_at: updated_at
  - created_at: created_at
  - extra: extra

**Example Update Server: JSON response**

.. literalinclude:: samples/servers/server-update-resp.json
   :language: javascript


Delete Server
===============

.. rest_method:: DELETE /servers/{server_uuid}

Deletes a server.

Preconditions

- The server must exist.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - server_uuid: server_ident

Response
--------

No body content is returned on a successful DELETE.
