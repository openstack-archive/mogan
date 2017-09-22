.. -*- rst -*-

====================
 Availability Zones
====================

Lists availability zones.

List Availability Zone information
==================================

.. rest_method:: GET /availability_zones

Lists availability zone information.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Response
--------

.. rest_parameters:: parameters.yaml

  - availability_zones: availability_zones

|

**Example List availability zone information**

.. literalinclude:: samples/availability_zones/availability-zone-list-resp.json
   :language: javascript
