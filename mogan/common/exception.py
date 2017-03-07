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
from mogan.common.i18n import _LE
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
                LOG.exception(_LE('Exception in string format operation'))
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
    msg_fmt = _("Forbidden")
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
    msg_fmt = _("Expected a uuid but received %(uuid)s.")


class InstanceTypeAlreadyExists(MoganException):
    _msg_fmt = _("InstanceType with uuid %(uuid)s already exists.")


class InstanceTypeNotFound(NotFound):
    msg_fmt = _("InstanceType %(type_id)s could not be found.")


class InstanceAlreadyExists(MoganException):
    _msg_fmt = _("Instance with name %(name)s already exists.")


class InstanceNotFound(NotFound):
    msg_fmt = _("Instance %(instance)s could not be found.")


class NodeNotFound(NotFound):
    msg_fmt = _("Node associated with instance %(instance)s "
                "could not be found.")


class InvalidActionParameterValue(Invalid):
    msg_fmt = _("The Parameter value: %(value)s for %(action) action of "
                "instance %(instance)s is invalid.")


class InstanceDeployFailure(Invalid):
    msg_fmt = _("Failed to deploy instance: %(reason)s")


class NoFreeEngineWorker(TemporaryFailure):
    _msg_fmt = _('Requested action cannot be performed due to lack of free '
                 'engine workers.')
    code = http_client.SERVICE_UNAVAILABLE


class DuplicateName(Conflict):
    _msg_fmt = _("A instance with name %(name)s already exists.")


class KeystoneUnauthorized(MoganException):
    _msg_fmt = _("Not authorized in Keystone.")


class KeystoneFailure(MoganException):
    pass


class CatalogNotFound(MoganException):
    _msg_fmt = _("Service type %(service_type)s with endpoint type "
                 "%(endpoint_type)s not found in keystone service catalog.")


class SchedulerNodeFilterNotFound(NotFound):
    message = _("Scheduler Node Filter %(filter_name)s could not be found.")


class SchedulerNodeWeigherNotFound(NotFound):
    message = _("Scheduler Node Weigher %(weigher_name)s could not be found.")


class NoValidNode(MoganException):
    message = _("No valid node was found. %(reason)s")


class TypeExtraSpecUpdateCreateFailed(MoganException):
    msg_fmt = _("Instance Type %(id)s extra spec cannot be updated or"
                "created after %(retries)d retries.")


class InstanceTypeExtraSpecsNotFound(NotFound):
    msg_fmt = _("Instance Type %(type_id)s has no extra specs with "
                "key %(extra_specs_key)s.")


class InterfacePlugException(MoganException):
    msg_fmt = _("Interface plugin failed")


class NetworkError(MoganException):
    _msg_fmt = _("Network operation failure.")


class ValidationError(Invalid):
    msg_fmt = "%(detail)s"


class ImageNotAuthorized(MoganException):
    msg_fmt = _("Not authorized for image %(image_id)s.")


class ImageBadRequest(Invalid):
    msg_fmt = _("Request of image %(image_id)s got BadRequest response: "
                "%(response)s")


class ImageNotFound(NotFound):
    msg_fmt = _("Image %(image_id)s could not be found.")


class GlanceConnectionFailed(MoganException):
    msg_fmt = _("Connection to glance host %(server)s failed: "
                "%(reason)s")


class PatchError(Invalid):
    _msg_fmt = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class AZNotFound(NotFound):
    msg_fmt = _("The availability zone could not be found.")


class InvalidState(Invalid):
    _msg_fmt = _("Invalid resource state.")


class DuplicateState(Conflict):
    _msg_fmt = _("Resource already exists.")


class PortNotFound(NotFound):
    msg_fmt = _("Port id %(port_id)s could not be found.")


class FloatingIpNotFoundForAddress(NotFound):
    msg_fmt = _("Floating IP not found for address %(address)s.")


class FloatingIpMultipleFoundForAddress(MoganException):
    msg_fmt = _("Multiple floating IPs are found for address %(address)s.")


class NetworkNotFound(NotFound):
    msg_fmt = _("Network %(network_id)s could not be found.")


class NetworkRequiresSubnet(Invalid):
    msg_fmt = _("Network %(network_uuid)s requires a subnet in order to boot"
                " instances on.")


class InstanceIsLocked(Invalid):
    msg_fmt = _("Instance %(instance_uuid)s is locked")


class InstanceInMaintenance(Invalid):
    msg_fmt = _("Instance %(instance_uuid)s is in maintenance mode")


class InvalidReservationExpiration(Invalid):
    message = _("Invalid reservation expiration %(expire)s.")


class QuotaNotFound(NotFound):
    message = _("Quota %(quota_name)s could not be found.")


class ProjectQuotaNotFound(QuotaNotFound):
    message = _("Quota for project %(project_id)s could not be found.")


class QuotaResourceUnknown(QuotaNotFound):
    message = _("Unknown quota resources %(unknown)s.")


class OverQuota(MoganException):
    message = _("Quota exceeded for resources: %(overs)s")


class PortLimitExceeded(OverQuota):
    msg_fmt = _("Maximum number of ports exceeded")


class QuotaAlreadyExists(MoganException):
    _msg_fmt = _("Quota with name %(name)s and project %(project_id)s already"
                 " exists.")


class ReservationAlreadyExists(MoganException):
    _msg_fmt = _("Reservation with name %(name)s and project %(project_id)s "
                 "already exists.")


class ReservationNotFound(NotFound):
    message = _("Reservation %(uuid)s could not be found.")


class InvalidToken(Invalid):
    msg_fmt = _("Invalid token: %(token)s")


class ConsoleNotAvailable(MoganException):
    _msg_fmt = _("Console not available.")


ObjectActionError = obj_exc.ObjectActionError
