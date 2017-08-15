.. -*- rst -*-

========================
 Server Remote Consoles
========================

Create server remote console.

Create Remote Console
=====================

.. rest_method:: POST /v1/servers/{server_uuid}/remote_consoles

The API provides a unified request for creating a remote console. The user can
get a URL to connect the console from this API. The URL includes the token
which is used to get permission to access the console. Servers may support
different console protocols. To return a remote console using a specific
protocol, such as serial, set the ``protocol`` parameter to ``serial``. For the
same protocol, there may be different connection types such as ``serial protocal
and socat type`` or ``serial protocol and shellinabox type``.

Normal response code: 200

Error response codes: badRequest(400), unauthorized(401), forbidden(403), itemNotFound(404),
conflict(409), notImplemented(501)

Request
-------

.. rest_parameters:: parameters.yaml

    - server_uuid: server_ident
    - protocol: remote_console_protocol
    - type: remote_console_type

**Example Create Remote Socat Console: JSON request**

.. literalinclude:: samples/remote_consoles/create-shellinabox-console-req.json

Response
--------

.. rest_parameters:: parameters.yaml

    - protocol: remote_console_protocol
    - type: remote_console_type
    - url: remote_console_url

**Example Create Remote Socat Console: JSON response**

.. literalinclude:: samples/remote_consoles/create-shellinabox-console-resp.json
