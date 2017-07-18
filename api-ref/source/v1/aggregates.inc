.. -*- rst -*-

============
 Aggregates
============

Creates and manages node aggregates. An aggregate assigns metadata to
groups of compute nodes. Aggregates are only visible to the cloud provider.

List Aggregates
===============

.. rest_method:: GET /aggregates

Lists all aggregates.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Response
--------

.. rest_parameters:: parameters.yaml

   - aggregates: aggregates
   - name: aggregate_name
   - links: links
   - metadata: aggregate_metadata
   - uuid: aggregate_uuid
   - created_at: created_at
   - updated_at: updated_at

**Example List aggregates: JSON response**

.. literalinclude:: samples/aggregates/aggregates-list-resp.json
   :language: javascript

Create Aggregate
================

.. rest_method:: POST /aggregates

Creates an aggregate.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

   - name: aggregate_name
   - metadata: aggregate_metadata

**Example Create Aggregatei: JSON request**

.. literalinclude:: samples/aggregates/aggregate-create-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - name: aggregate_name
   - links: links
   - metadata: aggregate_metadata
   - uuid: aggregate_uuid
   - created_at: created_at
   - updated_at: updated_at

**Example Create Aggregate: JSON response**

.. literalinclude:: samples/aggregates/aggregate-create-post-resp.json
   :language: javascript

Update Aggregate
================

.. rest_method:: PATCH /aggregates/{aggregate_uuid}

Updates an aggregate.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

The BODY of the PATCH request must be a JSON PATCH document, adhering to
`RFC 6902 <https://tools.ietf.org/html/rfc6902>`_.

.. rest_parameters:: parameters.yaml

  - aggregate_uuid: aggregate_uuid_path

**Example Update Aggregate: JSON request**

.. literalinclude:: samples/aggregates/aggregate-update-put-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - name: aggregate_name
   - links: links
   - metadata: aggregate_metadata
   - uuid: aggregate_uuid
   - created_at: created_at
   - updated_at: updated_at

**Example Update Aggregate: JSON response**

.. literalinclude:: samples/aggregates/aggregate-update-put-resp.json
   :language: javascript

Show Aggregate Details
======================

.. rest_method:: GET /aggregates/{aggregate_uuid}

Shows details for an aggregate.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - aggregate_uuid: aggregate_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - name: aggregate_name
   - links: links
   - metadata: aggregate_metadata
   - uuid: aggregate_uuid
   - created_at: created_at
   - updated_at: updated_at

**Example Show Aggregate Details**

.. literalinclude:: samples/aggregates/aggregate-get-resp.json
   :language: javascript


Delete Aggregate
================

.. rest_method:: DELETE /aggregates/{aggregate_uuid}

Deletes an aggregate.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - aggregate_uuid: aggregate_uuid_path

Response
--------

No body content is returned on a successful DELETE.
