# Copyright 2010 OpenStack Foundation
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

"""Possible task states for instances.

Compute instance task states represent what is happening to the instance at the
current moment. These tasks can be generic, such as 'spawning', or specific,
such as 'block_device_mapping'. These task states allow for a better view into
what an instance is doing and should be displayed to users/administrators as
necessary.

"""

from nimble.objects import fields

# possible task states during create()
SCHEDULING = fields.InstanceTaskState.SCHEDULING
NETWORKING = fields.InstanceTaskState.NETWORKING
SPAWNING = fields.InstanceTaskState.SPAWNING

# possible task states during reboot()
REBOOTING = fields.InstanceTaskState.REBOOTING

# possible task states during power_off()
POWERING_OFF = fields.InstanceTaskState.POWERING_OFF

# possible task states during power_on()
POWERING_ON = fields.InstanceTaskState.POWERING_ON

# possible task states during rebuild()
REBUILDING = fields.InstanceTaskState.REBUILDING

# possible task states during delete()
DELETING = fields.InstanceTaskState.DELETING
