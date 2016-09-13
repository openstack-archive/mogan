.. -*- rst -*-

========
 Flavor
========

Show and manage instance flavors.

Flavors are a way to describe the basic dimensions of a instance to be
created including how much ``cpu``, ``ram``, and ``disk space`` are
allocated to an instance built with this flavor.

List Flavors
============

.. rest_method:: GET /flavors

Lists all flavors accessible to your project.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml


Response
--------

.. rest_parameters:: parameters.yaml

   - flavors: flavors
   - id: flavor_id_body
   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public

**Example List Flavors**

Showing all the default flavors of a Liberty era Nova installation
that was not customized by the site operators.

.. literalinclude:: ../../doc/api_samples/flavors/flavors-list-resp.json
   :language: javascript


Create Flavor
=============

.. rest_method:: POST /flavors

Creates a flavor.

Creating a flavor is typically only available to administrators of a
cloud because this has implications for scheduling efficiently in the cloud.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

   - name: flavor_name
   - description: flavor_description
   - id: flavor_id_body_not_required
   - is_public: flavor_is_public_not_required
   - uuid: flavor_uuid_not_required

**Example Create Flavor**

.. literalinclude:: ../../doc/api_samples/flavors/flavor-create-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - flavors: flavors
   - id: flavor_id_body
   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public


**Example Create Flavor**

.. literalinclude:: ../../doc/api_samples/flavors/flavor-create-post-resp.json
   :language: javascript


Show Flavor Details
===================

.. rest_method:: GET /flavors/{flavor_uuid}

Shows details for a flavor.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - flavors: flavors
   - id: flavor_id_body
   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public

**Example Show Flavor Details**

.. literalinclude:: ../../doc/api_samples/flavors/flavor-get-resp.json
   :language: javascript


Delete Flavor
=============

.. rest_method:: DELETE /flavors/{flavor_uuid}

Deletes a flavor.

This is typically an admin only action. Deleting a flavor that is in use by
existing instances is not recommended as it can cause incorrect data to
be returned to the user under some operations.

Normal response codes: 202

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_id: flavor_uuid_path

Response
--------

No body content is returned on a successful DELETE.
