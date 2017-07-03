.. -*- rst -*-

===================
 Manageable Servers
===================

Lists manageable servers.

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

|

**Example List manageable servers information**

.. literalinclude:: samples/manageable_servers/manageable-servers-list-resp.json
   :language: javascript
