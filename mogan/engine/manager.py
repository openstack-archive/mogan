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

import threading

from ironicclient import exc as ironic_exc
from oslo_log import log
import oslo_messaging as messaging
from oslo_service import loopingcall
from oslo_service import periodic_task
import six

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common.i18n import _LW
from mogan.conf import CONF
from mogan.engine.baremetal import ironic
from mogan.engine.baremetal import ironic_states
from mogan.engine import base_manager
from mogan.engine.flows import create_instance
from mogan.engine import status

LOG = log.getLogger(__name__)

_UNPROVISION_STATES = (ironic_states.ACTIVE, ironic_states.DEPLOYFAIL,
                       ironic_states.ERROR, ironic_states.DEPLOYWAIT,
                       ironic_states.DEPLOYING)


class EngineManager(base_manager.BaseEngineManager):
    """Mogan Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)
    _lock = threading.Lock()

    def _refresh_cache(self):
        node_cache = {}
        nodes = ironic.get_node_list(self.ironicclient, detail=True,
                                     maintenance=False,
                                     provision_state=ironic_states.AVAILABLE,
                                     associated=False, limit=0)
        for node in nodes:
            node_cache[node.uuid] = node

        with self._lock:
            self.node_cache = node_cache

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval,
        run_immediately=True)
    def _sync_node_resources(self, context):
        self._refresh_cache()

    def _set_instance_obj_error_state(self, context, instance):
        try:
            instance.status = status.ERROR
            instance.save()
        except exception.InstanceNotFound:
            LOG.debug('Instance has been destroyed from under us while '
                      'trying to set it to ERROR', instance=instance)

    def destroy_networks(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(network_info)s",
                  {'uuid': instance.uuid,
                   'network_info': str(instance.network_info)})

        ports = instance.network_info.keys()
        for port in ports:
            self.network_api.delete_port(context, port, instance.uuid)

        ironic_ports = ironic.get_ports_from_node(self.ironicclient,
                                                  instance.node_uuid,
                                                  detail=True)
        for pif in ironic_ports:
            if 'vif_port_id' in pif.extra:
                ironic.unplug_vif(self.ironicclient, pif.uuid)

    def _destroy_instance(self, context, instance):
        try:
            ironic.destroy_node(self.ironicclient, instance.node_uuid)
        except Exception as e:
            # if the node is already in a deprovisioned state, continue
            # This should be fixed in Ironic.
            # TODO(deva): This exception should be added to
            #             python-ironicclient and matched directly,
            #             rather than via __name__.
            if getattr(e, '__name__', None) != 'InstanceDeployFailure':
                raise

        # using a dict because this is modified in the local method
        data = {'tries': 0}

        def _wait_for_provision_state():

            try:
                node = ironic.get_node_by_instance(self.ironicclient,
                                                   instance.uuid)
            except ironic_exc.NotFound:
                LOG.debug("Instance already removed from Ironic",
                          instance=instance)
                raise loopingcall.LoopingCallDone()
            LOG.debug('Current ironic node state is %s', node.provision_state)
            if node.provision_state in (ironic_states.NOSTATE,
                                        ironic_states.CLEANING,
                                        ironic_states.CLEANWAIT,
                                        ironic_states.CLEANFAIL,
                                        ironic_states.AVAILABLE):
                # From a user standpoint, the node is unprovisioned. If a node
                # gets into CLEANFAIL state, it must be fixed in Ironic, but we
                # can consider the instance unprovisioned.
                LOG.debug("Ironic node %(node)s is in state %(state)s, "
                          "instance is now unprovisioned.",
                          dict(node=node.uuid, state=node.provision_state),
                          instance=instance)
                raise loopingcall.LoopingCallDone()

            if data['tries'] >= CONF.ironic.api_max_retries + 1:
                msg = (_("Error destroying the instance on node %(node)s. "
                         "Provision state still '%(state)s'.")
                       % {'state': node.provision_state,
                          'node': node.uuid})
                LOG.error(msg)
                raise exception.MoganException(msg)
            else:
                data['tries'] += 1

        # wait for the state transition to finish
        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_provision_state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

        LOG.info(_LI('Successfully destroyed Ironic node %s'),
                 instance.node_uuid)

    def _remove_instance_info_from_node(self, instance):
        try:
            ironic.unset_instance_info(self.ironicclient, instance)
        except ironic_exc.BadRequest as e:
            LOG.warning(_LW("Failed to remove deploy parameters from node "
                            "%(node)s when unprovisioning the instance "
                            "%(instance)s: %(reason)s"),
                        {'node': instance.node_uuid, 'instance': instance.uuid,
                         'reason': six.text_type(e)})

    def create_instance(self, context, instance, requested_networks,
                        request_spec=None, filter_properties=None):
        """Perform a deployment."""
        LOG.debug("Starting instance...", instance=instance)

        if filter_properties is None:
            filter_properties = {}

        try:
            flow_engine = create_instance.get_flow(
                context,
                self,
                instance,
                requested_networks,
                request_spec,
                filter_properties,
            )
        except Exception:
            msg = _("Create manager instance flow failed.")
            LOG.exception(msg)
            raise exception.MoganException(msg)

        def _run_flow():
            # This code executes create instance flow. If something goes wrong,
            # flow reverts all job that was done and reraises an exception.
            # Otherwise, all data that was generated by flow becomes available
            # in flow engine's storage.
            with flow_utils.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()

        try:
            _run_flow()
        except Exception as e:
            self._set_instance_obj_error_state(context, instance)
            LOG.error(_LE("Created instance %(uuid)s failed."
                          "Exception: %(exception)s"),
                      {"uuid": instance.uuid,
                       "exception": e})
        else:
            LOG.info(_LI("Created instance %s successfully."), instance.uuid)
        finally:
            return instance

    def delete_instance(self, context, instance):
        """Delete an instance."""
        LOG.debug("Deleting instance...")

        try:
            node = ironic.get_node_by_instance(self.ironicclient,
                                               instance.uuid)
        except ironic_exc.NotFound:
            node = None

        if node:
            try:
                if node.provision_state in _UNPROVISION_STATES:
                    self.destroy_networks(context, instance)
                    self._destroy_instance(context, instance)
                else:
                    self._remove_instance_info_from_node(instance)
            except Exception:
                LOG.exception(_LE("Error while trying to clean up "
                                  "instance resources."),
                              instance=instance)

        instance.status = status.DELETED
        instance.save()
        instance.destroy()

    def _instance_states(self, context, instance):
        states = ironic.get_node_states(self.ironicclient,
                                        instance.node_uuid)
        LOG.info(_LI('Successfully get ironic node states: %s'),
                 states)
        return states.to_dict()

    def instance_states(self, context, instance):
        """Get an instance states."""
        LOG.debug("get instance states")

        return self._instance_states(context, instance)

    def _set_power_state(self, context, instance, state):
        ironic.set_power_state(self.ironicclient, instance.node_uuid, state)
        LOG.info(_LI('Successfully set ironic node power state: %s'),
                 state)

    def set_power_state(self, context, instance, state):
        """Get an instance states."""
        LOG.debug("set power state...")

        return self._set_power_state(context, instance, state)

    @messaging.expected_exceptions(exception.NodeNotFound)
    def get_ironic_node(self, context, instance_uuid, fields):
        """Get a ironic node."""
        try:
            node = ironic.get_node_by_instance(self.ironicclient,
                                               instance_uuid, fields)
        except ironic_exc.NotFound:
            msg = (_("Error retrieving the node by instance %(instance)s.")
                   % {'instance': instance_uuid})
            LOG.debug(msg)
            raise exception.NodeNotFound(msg)

        return node.to_dict()

    def get_ironic_node_list(self, context, fields):
        """Get an ironic node list."""
        nodes = ironic.get_node_list(self.ironicclient, associated=True,
                                     limit=0, fields=fields)
        return {'nodes': [node.to_dict() for node in nodes]}

    def list_availability_zones(self, context):
        """Get availability zone list."""
        with self._lock:
            node_cache = self.node_cache.values()

        azs = set()
        for node in node_cache:
            az = node.properties.get('availability_zone')
            if az is not None:
                azs.add(az)

        return {'availability_zones': list(azs)}
