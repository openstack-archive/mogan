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

"""
Mapping of bare metal instance states.

Setting the instance `power_state` is handled by the engine's power
synchronization thread. Based on the power state retrieved from the
hypervisor for the instance.
"""

from oslo_log import log as logging

from mogan.common import fsm

LOG = logging.getLogger(__name__)

#################
# Instance states
#################

""" Mapping of state-changing events that are PUT to the REST API

This is a mapping of target states which are PUT to the API.

This provides a reference set of supported actions, and in the future
may be used to support renaming these actions.
"""

ACTIVE = 'active'
""" The server is active """

BUILDING = 'building'
""" The server has not finished the original build process """

DELETED = 'deleted'
""" The server is permanently deleted """

DELETING = 'deleting'
""" The server has not finished the original delete process """

ERROR = 'error'
""" The server is in error """

POWERING_ON = 'powering-on'
""" The server is in powering on """

POWERING_OFF = 'powering-off'
""" The server is in powering off """

REBOOTING = 'rebooting'
""" The server is in rebooting """

STOPPED = 'stopped'
""" The server is powered off """

REBUILDING = 'rebuilding'
""" The server is in rebuilding process """

STABLE_STATES = (ACTIVE, ERROR, DELETED, STOPPED)
"""States that will not transition unless receiving a request."""

UNSTABLE_STATES = (BUILDING, DELETING, POWERING_ON, POWERING_OFF, REBOOTING,
                   REBUILDING)
"""States that can be changed without external request."""


#####################
# State machine model
#####################
def on_exit(old_state, event):
    """Used to log when a state is exited."""
    LOG.debug("Exiting old state '%s' in response to event '%s'",
              old_state, event)


def on_enter(new_state, event):
    """Used to log when entering a state."""
    LOG.debug("Entering new state '%s' in response to event '%s'",
              new_state, event)

watchers = {}
watchers['on_exit'] = on_exit
watchers['on_enter'] = on_enter

machine = fsm.FSM()

# Add stable states
for state in STABLE_STATES:
    machine.add_state(state, stable=True, **watchers)


# Add build* states
machine.add_state(BUILDING, target=ACTIVE, **watchers)

# Add delete* states
machine.add_state(DELETING, target=DELETED, **watchers)

# Add rebuild* states
machine.add_state(REBUILDING, target=ACTIVE, **watchers)

# Add power on* states
machine.add_state(POWERING_ON, target=ACTIVE, **watchers)

# Add power off* states
machine.add_state(POWERING_OFF, target=STOPPED, **watchers)

# Add reboot* states
machine.add_state(REBOOTING, target=ACTIVE, **watchers)


# from active* states
machine.add_transition(ACTIVE, REBUILDING, 'rebuild')
machine.add_transition(ACTIVE, POWERING_OFF, 'stop')
machine.add_transition(ACTIVE, REBOOTING, 'reboot')
machine.add_transition(ACTIVE, DELETING, 'delete')

# from stopped* states
machine.add_transition(STOPPED, POWERING_ON, 'start')
machine.add_transition(STOPPED, REBUILDING, 'rebuild')
machine.add_transition(STOPPED, DELETING, 'delete')

# from error* states
machine.add_transition(ERROR, DELETING, 'delete')

# from *ing states
machine.add_transition(BUILDING, ACTIVE, 'done')
machine.add_transition(DELETING, DELETED, 'done')
machine.add_transition(REBUILDING, ACTIVE, 'done')
machine.add_transition(POWERING_ON, ACTIVE, 'done')
machine.add_transition(POWERING_OFF, STOPPED, 'done')
machine.add_transition(REBOOTING, ACTIVE, 'done')

# All unstable states are allowed to transition to ERROR
for state in UNSTABLE_STATES:
    machine.add_transition(state, ERROR, 'error')
