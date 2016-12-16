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

"""Nimble base exception handling.

SHOULD include dedicated exception logging.

"""

from oslo_log import log as logging
from oslo_versionedobjects import exception as obj_exc
import six
from six.moves import http_client

from nimble.common.i18n import _
from nimble.common.i18n import _LE
from nimble.conf import CONF

LOG = logging.getLogger(__name__)


class NimbleException(Exception):
    """Base Nimble Exception

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

        super(NimbleException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well."""
        if not six.PY3:
            return unicode(self.args[0]).encode('utf-8')

        return self.args[0]

    def __unicode__(self):
        """Return a unicode representation of the exception message."""
        return unicode(self.args[0])


class NotAuthorized(NimbleException):
    _msg_fmt = _("Not authorized.")
    code = http_client.FORBIDDEN


class OperationNotPermitted(NotAuthorized):
    _msg_fmt = _("Operation not permitted.")


class HTTPForbidden(NotAuthorized):
    _msg_fmt = _("Access was denied to the following resource: %(resource)s")


class NotFound(NimbleException):
    _msg_fmt = _("Resource could not be found.")
    code = http_client.NOT_FOUND


class Invalid(NimbleException):
    _msg_fmt = _("Unacceptable parameters.")
    code = http_client.BAD_REQUEST


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    _msg_fmt = _("%(err)s")


class Conflict(NimbleException):
    _msg_fmt = _('Conflict.')
    code = http_client.CONFLICT


class TemporaryFailure(NimbleException):
    _msg_fmt = _("Resource temporarily unavailable, please retry.")
    code = http_client.SERVICE_UNAVAILABLE


class NotAcceptable(NimbleException):
    _msg_fmt = _("Request not acceptable.")
    code = http_client.NOT_ACCEPTABLE


class ConfigInvalid(NimbleException):
    _msg_fmt = _("Invalid configuration file. %(error_msg)s")


class InvalidMAC(Invalid):
    _msg_fmt = _("Expected a MAC address but received %(mac)s.")


class InvalidUUID(Invalid):
    msg_fmt = _("Expected a uuid but received %(uuid)s.")


class InstanceTypeAlreadyExists(NimbleException):
    _msg_fmt = _("InstanceType with uuid %(uuid)s already exists.")


class InstanceTypeNotFound(NotFound):
    msg_fmt = _("InstanceType %(type_id)s could not be found.")


class InstanceAlreadyExists(NimbleException):
    _msg_fmt = _("Instance with name %(name)s already exists.")


class InstanceNotFound(NotFound):
    msg_fmt = _("Instance %(instance)s could not be found.")


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


class KeystoneUnauthorized(NimbleException):
    _msg_fmt = _("Not authorized in Keystone.")


class KeystoneFailure(NimbleException):
    pass


class CatalogNotFound(NimbleException):
    _msg_fmt = _("Service type %(service_type)s with endpoint type "
                 "%(endpoint_type)s not found in keystone service catalog.")


class SchedulerNodeFilterNotFound(NotFound):
    message = _("Scheduler Node Filter %(filter_name)s could not be found.")


class SchedulerNodeWeigherNotFound(NotFound):
    message = _("Scheduler Node Weigher %(weigher_name)s could not be found.")


class NoValidNode(NimbleException):
    message = _("No valid node was found. %(reason)s")


class TypeExtraSpecUpdateCreateFailed(NimbleException):
    msg_fmt = _("Instance Type %(id)s extra spec cannot be updated or"
                "created after %(retries)d retries.")


class InstanceTypeExtraSpecsNotFound(NotFound):
    msg_fmt = _("Instance Type %(type_id)s has no extra specs with "
                "key %(extra_specs_key)s.")


class InterfacePlugException(NimbleException):
    msg_fmt = _("Interface plugin failed")


class NetworkError(NimbleException):
    _msg_fmt = _("Network operation failure.")


class ValidationError(Invalid):
    msg_fmt = "%(detail)s"


class ImageNotAuthorized(NimbleException):
    msg_fmt = _("Not authorized for image %(image_id)s.")


class ImageBadRequest(Invalid):
    msg_fmt = _("Request of image %(image_id)s got BadRequest response: "
                "%(response)s")


class ImageNotFound(NotFound):
    msg_fmt = _("Image %(image_id)s could not be found.")


class GlanceConnectionFailed(NimbleException):
    msg_fmt = _("Connection to glance host %(server)s failed: "
                "%(reason)s")


class PatchError(Invalid):
    _msg_fmt = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


ObjectActionError = obj_exc.ObjectActionError
