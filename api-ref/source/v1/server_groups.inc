.. -*- rst -*-

=============
 ServerGroups
=============

Lists, creates, shows and deletes server groups.

List ServerGroups
=================

.. rest_method:: GET /server_groups

Lists server groups.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Response
--------

.. rest_parameters:: parameters.yaml

   - server_groups: server_groups
   - name: server_group_name
   - links: links
   - uuid: server_group_uuid
   - policies: server_group_policies
   - members: server_group_members
   - project_id: project_id_body
   - user_id: user_id_body
   - created_at: created_at
   - updated_at: updated_at

**Example List server groups: JSON response**

.. literalinclude:: samples/server_groups/server-group-list-resp.json
   :language: javascript

Create ServerGroup
==================

.. rest_method:: POST /server_groups

Creates a server group.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

   - name: server_group_name
   - policies: server_group_policies

**Example Create a ServerGroup: JSON request**

.. literalinclude:: samples/server_groups/server-group-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - name: server_group_name
   - links: links
   - uuid: server_group_uuid
   - policies: server_group_policies
   - members: server_group_members
   - project_id: project_id_body
   - user_id: user_id_body
   - created_at: created_at
   - updated_at: updated_at

**Example Create ServerGroup: JSON response**

.. literalinclude:: samples/server_groups/server-group-post-resp.json
   :language: javascript


Show ServerGroup Details
========================

.. rest_method:: GET /server_groups/{server_group_uuid}

Shows details for a server group.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - server_group_uuid: server_group_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - name: server_group_name
   - links: links
   - uuid: server_group_uuid
   - policies: server_group_policies
   - members: server_group_members
   - project_id: project_id_body
   - user_id: user_id_body
   - created_at: created_at
   - updated_at: updated_at

**Example Show ServerGroup Details**

.. literalinclude:: samples/server_groups/server-group-get-resp.json
   :language: javascript


Delete a ServerGroup
====================

.. rest_method:: DELETE /server_groups/{server_group_uuid}

Deletes a server group.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - server_group_uuid: server_group_uuid_path

Response
--------

No body content is returned on a successful DELETE.
