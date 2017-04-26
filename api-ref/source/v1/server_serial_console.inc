.. -*- rst -*-

========================
 Server Serial Console
========================

Servers Serial Console can be managed through serial_console sub-resource.


Server Serial Console Summary
===============================

.. rest_method:: GET /v1/servers/{server_uuid}/serial_console

Get the console url info of the Server.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - console: console_info

**Example server network:**

.. literalinclude:: samples/server_console/server-serial-console-get.json
