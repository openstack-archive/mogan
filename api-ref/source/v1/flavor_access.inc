.. -*- rst -*-

================
 Flavors access
================

Lists tenants who have access to a private flavor and adds private
flavor access to and removes private flavor access from tenants. By
default, only administrators can manage private flavor access. A private
flavor has ``is_public`` set to ``false`` while a public flavor has
``is_public`` set to ``true``.

List Flavor Access Information For Given Flavor
===============================================

.. rest_method:: GET /flavors/{flavor_uuid}/access

Lists flavor access information.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path

Response
--------

.. rest_parameters:: parameters.yaml

   - flavor_access: flavor_access

**Example List Flavor Access Information For Given Flavor: JSON response**

.. literalinclude:: samples/flavor_access/flavor-access-list-resp.json
   :language: javascript

Add Flavor Access To Tenant
===========================

.. rest_method:: POST /flavors/{flavor_uuid}/access

Adds flavor access to a tenant and flavor.

Specify the ``tenant_id`` in the request body.

Normal response codes: 204

Error response codes: badRequest(400), unauthorized(401),
forbidden(403), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

  - flavor_uuid: flavor_uuid_path
  - tenant_id: tenant_id_body

**Example Add Flavor Access To Tenant: JSON response**

.. literalinclude:: samples/flavor_access/flavor-access-add-tenant-req.json
   :language: javascript

Response
--------

If successful, this method does not return content in the response body.

Remove Flavor Access From Tenant
================================

.. rest_method:: DELETE /flavors/{flavor_uuid}/access/{tenant_id}

Removes flavor access from a tenant and flavor.

Normal response codes: 204

Error response codes: badRequest(400), unauthorized(401), forbidden(403),
itemNotFound(404), conflict(409)

Request
-------

.. rest_parameters:: parameters.yaml

    - flavor_uuid: flavor_uuid_path
    - tenant_id: tenant_id_path

Response
--------

If successful, this method does not return content in the response body.
