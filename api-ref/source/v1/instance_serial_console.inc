.. -*- rst -*-

========================
 Instance Serial Console
========================

Instances Serial Console can be managed through serial_console sub-resource.


Instance Serial Console Summary
===============================

.. rest_method:: GET /v1/instances/{instance_uuid}/serial_console

Get the console url info of the Instance.

Normal response code: 200

Request
-------

.. rest_parameters:: parameters.yaml

    - instance_uuid: instance_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - console: console_info
  - url: console_url

**Example instance network:**

.. literalinclude:: samples/instance_console/instance-serial-console-get.json
