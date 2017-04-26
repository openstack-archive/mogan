.. -*- rst -*-

=========
 Flavors
=========

Show and manage server flavors.

Flavors are a way to describe the basic dimensions of a server to be
created including how much ``cpu``, ``ram``, and ``disk space`` are
allocated to a server built with this flavor.

List Flavors
============

.. rest_method:: GET /flavors

Lists all flavors accessible to your project.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------


Response
--------

.. rest_parameters:: parameters.yaml

   - flavors: flavors
   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public
   - extra_specs: flavor_extra_specs

**Example List flavors**

.. literalinclude:: samples/flavors/flavors-list-resp.json
   :language: javascript

Create Flavor
=============

.. rest_method:: POST /flavors

Creates a flavor.

Creating a flavor is typically only available to administrators of a
cloud because this has implications for scheduling efficiently in the cloud.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

   - name: flavor_name
   - description: flavor_description
   - is_public: flavor_is_public_not_required
   - uuid: flavor_uuid_not_required

**Example Create Flavor**

.. literalinclude:: samples/flavors/flavor-create-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public
   - extra_specs: flavor_extra_specs

**Example Create flavor**

.. literalinclude:: samples/flavors/flavor-create-post-resp.json
   :language: javascript

Update Flavor
=============

.. rest_method:: PUT /flavors/{flavor_uuid}

Updates a flavor.

Updating a flavor is typically only available to administrators of a
cloud because this has implications for scheduling efficiently in the cloud.

Normal response codes: 200

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path
  - name: flavor_name
  - description: flavor_description
  - is_public: flavor_is_public_not_required

**Example Update Flavor**

.. literalinclude:: samples/flavors/flavor-update-put-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public
   - extra_specs: flavor_extra_specs

**Example Update flavor**

.. literalinclude:: samples/flavors/flavor-update-put-resp.json
   :language: javascript

Show Server Flavor Details
==========================

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

   - name: flavor_name
   - links: links
   - description: flavor_description
   - uuid: flavor_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: flavor_is_public
   - extra_specs: flavor_extra_specs

**Example Show Flavor Details**

.. literalinclude:: samples/flavors/flavor-get-resp.json
   :language: javascript


Delete Flavor
=============

.. rest_method:: DELETE /flavors/{flavor_uuid}

Deletes a flavor.

This is typically an admin only action. Deleting a flavor that is in use by
existing servers is not recommended as it can cause incorrect data to
be returned to the user under some operations.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path

Response
--------

No body content is returned on a successful DELETE.


List Extra Specs
================

.. rest_method:: GET /flavors/{flavor_uuid}/extraspecs

Lists all extra specs related to the given flavor.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

    - flavor_uuid: flavor_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - extra_specs: flavor_extra_specs

**Example List Extra Specs**

.. literalinclude:: samples/flavors/flavor-extra-specs-list-resp.json
   :language: javascript


Create/Update Extra Spec
========================

.. rest_method:: PATCH /flavors/{flavor_uuid}/extraspecs

Create/update extra specs to the given flavor.

Normal response codes: 201

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

    - flavor_uuid: flavor_uuid_path
    - extra_specs: flavor_extra_specs

**Example Create Extra Specs**

.. literalinclude:: samples/flavors/flavor-extra-specs-patch-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - extra_specs: flavor_extra_specs

**Example Create Extra Specs**

.. literalinclude:: samples/flavors/flavor-extra-specs-patch-resp.json
   :language: javascript


Delete Extra Spec
=================

.. rest_method:: DELETE /flavors/{flavor_uuid}/extraspecs/key

Deletes an extra spec related to the specific flavor.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path
  - key: spec_key_path

Response
--------

No body content is returned on a successful DELETE.

