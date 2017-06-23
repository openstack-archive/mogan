# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Mogan base exception handling.

SHOULD include dedicated exception logging.

"""

from oslo_log import log as logging
from oslo_versionedobjects import exception as obj_exc
import six
from six.moves import http_client

from mogan.common.i18n import _
from mogan.conf import CONF

LOG = logging.getLogger(__name__)


class MoganException(Exception):
    """Base Mogan Exception

    To correctly use this class, inherit from it and define
    a '_msg_fmt' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    If you need to access the message from an exception you should use
    six.text_type(exc)

    """
    _msg_fmt = _("An unknown exception occurred.")
    code = http_client.INTERNAL_SERVER_ERROR
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self._msg_fmt % kwargs

            except Exception:
                # kwargs doesn't match a variable in self._msg_fmt
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise
                else:
                    # at least get the core self._msg_fmt out if something
                    # happened
                    message = self._msg_fmt

        super(MoganException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well."""
        if not six.PY3:
            return unicode(self.args[0]).encode('utf-8')

        return self.args[0]

    def __unicode__(self):
        """Return a unicode representation of the exception message."""
        return unicode(self.args[0])


class NotAuthorized(MoganException):
    _msg_fmt = _("Not authorized.")
    code = http_client.FORBIDDEN


class OperationNotPermitted(NotAuthorized):
    _msg_fmt = _("Operation not permitted.")


class Forbidden(MoganException):
    _msg_fmt = _("Forbidden")
    code = 403


class HTTPForbidden(NotAuthorized):
    _msg_fmt = _("Access was denied to the following resource: %(resource)s")


class NotFound(MoganException):
    _msg_fmt = _("Resource could not be found.")
    code = http_client.NOT_FOUND


class Invalid(MoganException):
    _msg_fmt = _("Unacceptable parameters.")
    code = http_client.BAD_REQUEST


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    _msg_fmt = _("%(err)s")


class Conflict(MoganException):
    _msg_fmt = _('Conflict.')
    code = http_client.CONFLICT


class TemporaryFailure(MoganException):
    _msg_fmt = _("Resource temporarily unavailable, please retry.")
    code = http_client.SERVICE_UNAVAILABLE


class NotAcceptable(MoganException):
    _msg_fmt = _("Request not acceptable.")
    code = http_client.NOT_ACCEPTABLE


class ConfigInvalid(MoganException):
    _msg_fmt = _("Invalid configuration file. %(error_msg)s")


class InvalidMAC(Invalid):
    _msg_fmt = _("Expected a MAC address but received %(mac)s.")


class InvalidUUID(Invalid):
    _msg_fmt = _("Expected a uuid but received %(uuid)s.")


class FlavorAlreadyExists(Conflict):
    _msg_fmt = _("Flavor with name %(name)s already exists.")


class FlavorNotFound(NotFound):
    _msg_fmt = _("Flavor %(flavor_id)s could not be found.")


class ServerAlreadyExists(Conflict):
    _msg_fmt = _("Server with name %(name)s already exists.")


class ServerNotFound(NotFound):
    _msg_fmt = _("Server %(server)s could not be found.")


class FlavorAccessExists(Conflict):
    _msg_fmt = _("Flavor access already exists for flavor %(flavor_id)s "
                 "and project %(project_id)s combination.")


class FlavorAccessNotFound(NotFound):
    _msg_fmt = _("Flavor access not found for %(flavor_id)s / "
                 "%(project_id)s combination.")


class ComputeNodeAlreadyExists(Conflict):
    _msg_fmt = _("ComputeNode with node_uuid %(node)s already exists.")


class ComputeNodeNotFound(NotFound):
    _msg_fmt = _("ComputeNode %(node)s could not be found.")


class ComputePortAlreadyExists(Conflict):
    _msg_fmt = _("ComputePort with port_uuid %(port)s already exists.")


class ComputePortNotFound(NotFound):
    _msg_fmt = _("ComputePort %(port)s could not be found.")


class ComputePortNotAvailable(NotFound):
    _msg_fmt = _("No available compute ports.")


class NodeNotFound(NotFound):
    _msg_fmt = _("Node associated with server %(server)s "
                 "could not be found.")


class InvalidActionParameterValue(Invalid):
    _msg_fmt = _("The Parameter value: %(value)s for %(action) action of "
                 "server %(server)s is invalid.")


class ServerDeployFailure(Invalid):
    _msg_fmt = _("Failed to deploy server: %(reason)s")


class ServerDeployAborted(Invalid):
    _msg_fmt = _("Server deployment is aborted: %(reason)s")


class NoFreeEngineWorker(TemporaryFailure):
    _msg_fmt = _('Requested action cannot be performed due to lack of free '
                 'engine workers.')
    code = http_client.SERVICE_UNAVAILABLE


class DuplicateName(Conflict):
    _msg_fmt = _("A server with name %(name)s already exists.")


class KeystoneUnauthorized(NotAuthorized):
    _msg_fmt = _("Not authorized in Keystone.")


class KeystoneFailure(MoganException):
    pass


class CatalogNotFound(NotFound):
    _msg_fmt = _("Service type %(service_type)s with endpoint type "
                 "%(endpoint_type)s not found in keystone service catalog.")


class SchedulerNodeFilterNotFound(NotFound):
    _msg_fmt = _("Scheduler Node Filter %(filter_name)s could not be found.")


class SchedulerNodeWeigherNotFound(NotFound):
    _msg_fmt = _("Scheduler Node Weigher %(weigher_name)s could not be found.")


class NoValidNode(NotFound):
    _msg_fmt = _("No valid node was found. %(reason)s")


class InterfacePlugException(MoganException):
    _msg_fmt = _("Interface plugin failed")


class NetworkError(MoganException):
    _msg_fmt = _("Network operation failure.")


class ValidationError(Invalid):
    _msg_fmt = "%(detail)s"


class ImageNotAuthorized(NotAuthorized):
    _msg_fmt = _("Not authorized for image %(image_id)s.")


class ImageBadRequest(Invalid):
    _msg_fmt = _("Request of image %(image_id)s got BadRequest response: "
                 "%(response)s")


class ImageNotFound(NotFound):
    _msg_fmt = _("Image %(image_id)s could not be found.")


class GlanceConnectionFailed(Invalid):
    _msg_fmt = _("Connection to glance host %(server)s failed: "
                 "%(reason)s")


class PatchError(Invalid):
    _msg_fmt = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class AZNotFound(NotFound):
    _msg_fmt = _("The availability zone could not be found.")


class InvalidState(Invalid):
    _msg_fmt = _("Invalid resource state.")


class DuplicateState(Conflict):
    _msg_fmt = _("Resource already exists.")


class PortNotFound(NotFound):
    _msg_fmt = _("Port id %(port_id)s could not be found.")


class PortRequiresFixedIP(Invalid):
    msg_fmt = _("Port %(port_id)s requires a FixedIP in order to be used.")


class PortInUse(Conflict):
    msg_fmt = _("Port %(port_id)s is still in use.")


class InterfaceAttachFailed(Conflict):
    msg_fmt = _("Failed to attach network adapter device to "
                "%(server_uuid)s")


class InterfaceNotFoundForServer(NotFound):
    _msg_fmt = _("Interface not found for server %(server)s.")


class InterfaceNotAttached(Invalid):
    _msg_fmt = _("Interface is not attached.")


class InterfaceDetachFailed(Invalid):
    _msg_fmt = _("Failed to detach network for %(server_uuid)s")


class FloatingIpNotFoundForAddress(NotFound):
    _msg_fmt = _("Floating IP not found for address %(address)s.")


class FloatingIpMultipleFoundForAddress(Conflict):
    _msg_fmt = _("Multiple floating IPs are found for address %(address)s.")


class NetworkNotFound(NotFound):
    _msg_fmt = _("Network %(network_id)s could not be found.")


class NetworkRequiresSubnet(Invalid):
    _msg_fmt = _("Network %(network_uuid)s requires a subnet in order to boot"
                 " servers on.")


class ServerIsLocked(Invalid):
    _msg_fmt = _("Server %(server_uuid)s is locked")


class ServerInMaintenance(Invalid):
    _msg_fmt = _("Server %(server_uuid)s is in maintenance mode")


class InvalidReservationExpiration(Invalid):
    _msg_fmt = _("Invalid reservation expiration %(expire)s.")


class QuotaNotFound(NotFound):
    _msg_fmt = _("Quota %(quota_name)s could not be found.")


class ProjectQuotaNotFound(QuotaNotFound):
    _msg_fmt = _("Quota for project %(project_id)s could not be found.")


class QuotaResourceUnknown(QuotaNotFound):
    _msg_fmt = _("Unknown quota resources %(unknown)s.")


class OverQuota(Forbidden):
    _msg_fmt = _("Quota exceeded for resources: %(overs)s")


class PortLimitExceeded(OverQuota):
    _msg_fmt = _("Maximum number of ports exceeded")


class QuotaAlreadyExists(Conflict):
    _msg_fmt = _("Quota with name %(name)s and project %(project_id)s already"
                 " exists.")


class ReservationAlreadyExists(Conflict):
    _msg_fmt = _("Reservation with name %(name)s and project %(project_id)s "
                 "already exists.")


class ReservationNotFound(NotFound):
    _msg_fmt = _("Reservation %(uuid)s could not be found.")


class InvalidToken(Invalid):
    _msg_fmt = _("Invalid token: %(token)s")


class ConsoleNotAvailable(MoganException):
    _msg_fmt = _("Console not available.")


class ConsoleTypeUnavailable(Invalid):
    _msg_fmt = _("Unavailable console type %(console_type)s.")


class ConfigDriveMountFailed(MoganException):
    _msg_fmt = _("Could not mount vfat config drive. %(operation)s failed. "
                 "Error: %(error)s")


class ConfigDriveUnknownFormat(Invalid):
    _msg_fmt = _("Unknown config drive format %(format)s. Select one of "
                 "iso9660 or vfat.")


class ServerUserDataTooLarge(Invalid):
    _msg_fmt = _("User data too large. User data must be no larger than "
                 "%(maxsize)s bytes once base64 encoded. Your data is "
                 "%(length)d bytes")


class ServerUserDataMalformed(Invalid):
    _msg_fmt = _("User data needs to be valid base 64.")


class Base64Exception(Invalid):
    _msg_fmt = _("Invalid Base 64 data for file %(path)s")


class KeyPairExists(Conflict):
    _msg_fmt = _("KeyPaire with key name %(key_name)s already exists.")


class KeypairNotFound(NotFound):
    _msg_fmt = _("Keypair %(name)s not found for user %(user_id)s")


class InvalidKeypair(Invalid):
    _msg_fmt = _("Keypair data is invalid: %(reason)s")


class InvalidInventory(Invalid):
    _msg_fmt = _("Inventory for '%(resource_class)s' on "
                 "resource provider '%(resource_provider)s' invalid.")


class InvalidResourceClass(Invalid):
    _msg_fmt = _("Resource class '%(resource_class)s' invalid.")


class InventoryInUse(InvalidInventory):
    _msg_fmt = _("Inventory for '%(resource_classes)s' on "
                 "resource provider '%(resource_provider)s' in use.")


class CannotDisassociateAutoAssignedFloatingIP(Forbidden):
    _msg_fmt = _("Cannot disassociate auto assigned floating "
                 "IP: %(floatingip)s")


class FloatingIpNotAssociated(Invalid):
    _msg_fmt = _("Floating IP: %(floatingip)s is not associated")


ObjectActionError = obj_exc.ObjectActionError
