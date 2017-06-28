# Copyright (c) 2016 Intel
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

"""Policy Engine For Mogan."""

import functools
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log
from oslo_policy import policy
from oslo_versionedobjects import base as object_base
import pecan
import sys
import wsme

from mogan.common import exception

_ENFORCER = None
CONF = cfg.CONF
LOG = log.getLogger(__name__)

default_policies = [
    # Legacy setting, don't remove. Likely to be overridden by operators who
    # forget to update their policy.json configuration file.
    # This gets rolled into the new "is_admin" rule below.
    policy.RuleDefault('admin_api',
                       'role:admin or role:administrator',
                       description='Legacy rule for cloud admin access'),
    # is_public_api is set in the environment from AuthTokenMiddleware
    policy.RuleDefault('public_api',
                       'is_public_api:True',
                       description='Internal flag for public API routes'),
    # Generic default to hide server secrets
    policy.RuleDefault('show_server_secrets',
                       '!',
                       description='Show or mask secrets within server information in API responses'),  # noqa
    # The policy check "@" will always accept an access. The empty list
    # (``[]``) or the empty string (``""``) is equivalent to the "@"
    policy.RuleDefault('allow',
                       '@',
                       description='any access will be passed'),
    # the policy check "!" will always reject an access.
    policy.RuleDefault('deny',
                       '!',
                       description='all access will be forbidden'),
    policy.RuleDefault('is_admin',
                       'rule:admin_api',  # noqa
                       description='Full read/write API access'),
    policy.RuleDefault('admin_or_owner',
                       'is_admin:True or project_id:%(project_id)s',
                       description='Admin or owner API access'),
    policy.RuleDefault('admin_or_user',
                       'is_admin:True or user_id:%(user_id)s',
                       description='Admin or user API access'),
    policy.RuleDefault('default',
                       'rule:admin_or_owner',
                       description='Default API access rule'),
]

# NOTE: to follow policy-in-code spec, we define defaults for
#             the granular policies in code, rather than in policy.json.
#             All of these may be overridden by configuration, but we can
#             depend on their existence throughout the code.

server_policies = [
    policy.RuleDefault('mogan:server:get',
                       'rule:default',
                       description='Retrieve Server records'),
    policy.RuleDefault('mogan:server:get_states',
                       'rule:default',
                       description='View Server power and provision state'),
    policy.RuleDefault('mogan:server:create',
                       'rule:allow',
                       description='Create Server records'),
    policy.RuleDefault('mogan:server:delete',
                       'rule:default',
                       description='Delete Server records'),
    policy.RuleDefault('mogan:server:update',
                       'rule:default',
                       description='Update Server records'),
    policy.RuleDefault('mogan:server:set_power_state',
                       'rule:default',
                       description='Perform the power action on a server'),
    policy.RuleDefault('mogan:server:get_networks',
                       'rule:default',
                       description='Get Server network information'),
    policy.RuleDefault('mogan:server:associate_floatingip',
                       'rule:default',
                       description='Associate a floating ip with a server'),
    policy.RuleDefault('mogan:server:disassociate_floatingip',
                       'rule:default',
                       description='Disassociate a floating ip'),
    policy.RuleDefault('mogan:server:set_lock_state',
                       'rule:default',
                       description='Lock/UnLock a server'),
    policy.RuleDefault('mogan:server:attach_interface',
                       'rule:default',
                       description='Attach an interface for an server'),
    policy.RuleDefault('mogan:server:set_provision_state',
                       'rule:default',
                       description='Set the provision state of a server'),
    policy.RuleDefault('mogan:server:get_serial_console',
                       'rule:default',
                       description='Get serial console for a server'),
    policy.RuleDefault('mogan:flavor:create',
                       'rule:admin_api',
                       description='Create flavor records'),
    policy.RuleDefault('mogan:flavor:update',
                       'rule:admin_api',
                       description='Update flavor records'),
    policy.RuleDefault('mogan:flavor:delete',
                       'rule:admin_api',
                       description='Delete flavor records'),
    policy.RuleDefault('mogan:flavor:get_all',
                       'rule:allow',
                       description='Retrieve all flavor records'),
    policy.RuleDefault('mogan:flavor:get_one',
                       'rule:allow',
                       description='Show flavor details'),
    policy.RuleDefault('mogan:flavor_access:add_tenant_access',
                       'rule:admin_api',
                       description='Add tenant access for flavor'),
    policy.RuleDefault('mogan:flavor_access:remove_tenant_access',
                       'rule:admin_api',
                       description='Remove tenant access for flavor'),
    policy.RuleDefault('mogan:flavor_access:get_all',
                       'rule:allow',
                       description='Retrieve all flavor access'),
    policy.RuleDefault('mogan:server:detach_interface',
                       'rule:default',
                       description='Detach a network interface'),
]


def list_policies():
    policies = (default_policies
                + server_policies)
    return policies


@lockutils.synchronized('policy_enforcer', 'mogan-')
def init_enforcer(policy_file=None, rules=None,
                  default_rule=None, use_conf=True):
    """Synchronously initializes the policy enforcer

       :param policy_file: Custom policy file to use, if none is specified,
                           `CONF.oslo_policy.policy_file` will be used.
       :param rules: Default dictionary / Rules to use. It will be
                     considered just in the first instantiation.
       :param default_rule: Default rule to use,
                            CONF.oslo_policy.policy_default_rule will
                            be used if none is specified.
       :param use_conf: Whether to load rules from config file.

    """
    global _ENFORCER

    if _ENFORCER:
        return

    # NOTE: Register defaults for policy-in-code here so that they are
    # loaded exactly once - when this module-global is initialized.
    # Defining these in the relevant API modules won't work
    # because API classes lack singletons and don't use globals.
    _ENFORCER = policy.Enforcer(CONF, policy_file=policy_file,
                                rules=rules,
                                default_rule=default_rule,
                                use_conf=use_conf)
    _ENFORCER.register_defaults(list_policies())


def get_enforcer():
    """Provides access to the single server of Policy enforcer."""

    if not _ENFORCER:
        init_enforcer()

    return _ENFORCER


# NOTE: We can't call these methods from within decorators because the
# 'target' and 'creds' parameter must be fetched from the call time
# context-local pecan.request magic variable, but decorators are compiled
# at module-load time.


def authorize(rule, target, creds, *args, **kwargs):
    """A shortcut for policy.Enforcer.authorize()

    Checks authorization of a rule against the target and credentials, and
    raises an exception if the rule is not defined.

    Beginning with the Newton cycle, this should be used in place of 'enforce'.
    """
    enforcer = get_enforcer()
    try:
        return enforcer.authorize(rule, target, creds, do_raise=True,
                                  *args, **kwargs)
    except policy.PolicyNotAuthorized:
        raise exception.HTTPForbidden(resource=rule)


# NOTE(Shaohe Feng): This decorator MUST appear first (the outermost
# decorator) on an API method for it to work correctly
def authorize_wsgi(api_name, act=None, need_target=True):
    """This is a decorator to simplify wsgi action policy rule check.

        :param api_name: The collection name to be evaluate.
        :param act: The function name of wsgi action.
        :param need_target: Whether need target for authorization. Such as,
               when create some resource , maybe target is not needed.
       example:
           from mogan.common import policy
           class ServersController(rest.RestController):
               ....
               @policy.authorize_wsgi("mogan:server", "delete")
               @wsme_pecan.wsexpose(None, types.uuid_or_name, status_code=204)
               def delete(self, bay_ident):
                   ...
    """
    def wraper(fn):
        action = "%s:%s" % (api_name, (act or fn.__name__))

        # In this authorize method, we return a dict data when authorization
        # fails or exception comes out. Maybe we can consider to use
        # wsme.api.Response in future.
        def return_error(resp_status):
            exception_info = sys.exc_info()
            orig_exception = exception_info[1]
            orig_code = getattr(orig_exception, 'code', None)
            pecan.response.status = orig_code or resp_status
            data = wsme.api.format_exception(
                exception_info,
                pecan.conf.get('wsme', {}).get('debug', False)
            )
            del exception_info
            return data

        @functools.wraps(fn)
        def handle(self, *args, **kwargs):
            context = pecan.request.context
            credentials = context.to_policy_values()
            credentials['is_admin'] = context.is_admin
            target = {}
            # maybe we can pass "_get_resource" to authorize_wsgi
            if need_target and hasattr(self, "_get_resource"):
                try:
                    resource = getattr(self, "_get_resource")(*args, **kwargs)
                    # just support object, other type will just keep target as
                    # empty, then follow authorize method will fail and throw
                    # an exception
                    if isinstance(resource,
                                  object_base.VersionedObjectDictCompat):
                        target = {'project_id': resource.project_id,
                                  'user_id': resource.user_id}
                except Exception:
                    return return_error(500)
            elif need_target:
                # if developer do not set _get_resource, just set target as
                # empty, then follow authorize method will fail and throw an
                # exception
                target = {}
            else:
                # for create method, before resource exsites, we can check the
                # the credentials with itself.
                target = {'project_id': context.tenant,
                          'user_id': context.user}
            try:
                authorize(action, target, credentials)
            except Exception:
                return return_error(403)
            return fn(self, *args, **kwargs)
        return handle

    return wraper


def check(rule, target, creds, *args, **kwargs):
    """A shortcut for policy.Enforcer.enforce()

    Checks authorization of a rule against the target and credentials
    and returns True or False.
    """
    enforcer = get_enforcer()
    return enforcer.enforce(rule, target, creds, *args, **kwargs)


def enforce(rule, target, creds, do_raise=False, exc=None, *args, **kwargs):
    """A shortcut for policy.Enforcer.enforce()

    Checks authorization of a rule against the target and credentials.

    """
    # NOTE: this method is obsoleted by authorize(), but retained for
    # backwards compatibility in case it has been used downstream.
    # It may be removed in the Pike cycle.
    LOG.warning("Deprecation warning: calls to mogan.common.policy.enforce() "
                "should be replaced with authorize(). This method may be "
                "removed in a future release.")

    enforcer = get_enforcer()
    return enforcer.enforce(rule, target, creds, do_raise=do_raise,
                            exc=exc, *args, **kwargs)
