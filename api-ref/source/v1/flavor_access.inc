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

.. literalinclude:: samples/flavor-access/flavor-access-list-resp.json
   :language: javascript
