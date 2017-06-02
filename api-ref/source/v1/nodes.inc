.. -*- rst -*-

===============
 Compute Nodes
===============

Lists compute nodes.

List Compute Node information
=============================

.. rest_method:: GET /nodes

Lists compute node information.

Normal response codes: 200

Error response codes: unauthorized(401), forbidden(403)

Response
--------

.. rest_parameters:: parameters.yaml

  - nodes: nodes

|

**Example List compute node information**

.. literalinclude:: samples/nodes/node-list-resp.json
   :language: javascript
