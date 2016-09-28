.. -*- rst -*-

======
 Type
======

Show and manage Types.

Types are a way to describe the basic dimensions of a instance to be
created including how much ``cpu``, ``ram``, and ``disk space`` are
allocated to an instance built with this type.

List Types
==========

.. rest_method:: GET /types

Lists all types accessible to your project.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------


Response
--------

.. rest_parameters:: parameters.yaml

   - types: types
   - id: type_id_body
   - name: type_name
   - links: links
   - description: type_description
   - uuid: type_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: type_is_public
   - extra_specs: type_extra_specs

**Example List types**

.. literalinclude:: ../../doc/api_samples/types/types-list-resp.json
   :language: javascript

Create Type
===========

.. rest_method:: POST /types

Creates a type.

Creating a type is typically only available to administrators of a
cloud because this has implications for scheduling efficiently in the cloud.

Normal response codes: 201

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

   - name: type_name
   - description: type_description
   - id: type_id_body_not_required
   - is_public: type_is_public_not_required
   - uuid: type_uuid_not_required

**Example Create Type**

.. literalinclude:: ../../doc/api_samples/types/type-create-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - id: type_id_body
   - name: type_name
   - links: links
   - description: type_description
   - uuid: type_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: type_is_public
   - extra_specs: type_extra_specs

**Example Create type**

.. literalinclude:: ../../doc/api_samples/types/type-create-post-resp.json
   :language: javascript


Show Type Details
===================

.. rest_method:: GET /types/{type_uuid}

Shows details for a type.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - type_uuid: type_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - id: type_id_body
   - name: type_name
   - links: links
   - description: type_description
   - uuid: type_uuid
   - created_at: created_at
   - updated_at: updated_at
   - is_public: type_is_public
   - extra_specs: type_extra_specs

**Example Show type Details**

.. literalinclude:: ../../doc/api_samples/types/type-get-resp.json
   :language: javascript


Delete Type
=============

.. rest_method:: DELETE /types/{type_uuid}

Deletes a type.

This is typically an admin only action. Deleting a type that is in use by
existing instances is not recommended as it can cause incorrect data to
be returned to the user under some operations.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - type_uuid: type_uuid_path

Response
--------

No body content is returned on a successful DELETE.


List Extra Specs
================

.. rest_method:: GET /types/{type_uuid}/extraspecs

Lists all extra specs related to the given type.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

    - type_uuid: type_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - extra_specs: type_extra_specs

**Example List Extra Specs**

.. literalinclude:: ../../doc/api_samples/types/type-extra-specs-list-resp.json
   :language: javascript


Create Extra Spec
=================

.. rest_method:: POST /types/{type_uuid}/extraspecs

Create extra specs to the given type.

Normal response codes: 201

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

    - type_uuid: type_uuid_path
    - extra_specs: type_extra_specs

**Example Create Extra Specs**

.. literalinclude:: ../../doc/api_samples/types/type-extra-specs-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - extra_specs: type_extra_specs

**Example Create Extra Specs**

.. literalinclude:: ../../doc/api_samples/types/type-extra-specs-list-resp.json
   :language: javascript


Update Extra Spec
=================

.. rest_method:: PUT /types/{type_uuid}/extraspecs

Updates extra specs to the given type.

Normal response codes: 202

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

    - type_uuid: type_uuid_path
    - extra_specs: type_extra_specs

**Example Update Extra Specs**

.. literalinclude:: ../../doc/api_samples/types/type-extra-specs-post-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

    - extra_specs: type_extra_specs

**Example Update Extra Specs**

.. literalinclude:: ../../doc/api_samples/types/type-extra-specs-list-resp.json
   :language: javascript


Delete Extra Spec
=================

.. rest_method:: DELETE /types/{type_uuid}/extraspecs/key

Deletes an extra spec related to the specific type.

Normal response codes: 204

Error response codes: unauthorized(401), forbidden(403), itemNotFound(404)

Request
-------

.. rest_parameters:: parameters.yaml

  - type_id: type_uuid_path
  - key: spec_key_path

Response
--------

No body content is returned on a successful DELETE.

