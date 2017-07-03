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
  - uuid: manageable_servers_uuid
  - name: manageable_servers_name
  - resource_class: manageable_servers_resource_class
  - power_state: manageable_servers_power_state
  - provision_state: manageable_servers_provision_state
  - ports: manageable_servers_ports
  - portgroups: manageable_servers_portgroups
  - image_source: manageable_servers_image_source

|

**Example List manageable servers information**

.. literalinclude:: samples/manageable_servers/manageable-servers-list-resp.json
   :language: javascript
