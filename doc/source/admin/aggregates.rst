..
      Copyright 2012 OpenStack Foundation
      Copyright 2012 Citrix Systems, Inc.
      Copyright 2012, The Cloudscaling Group, Inc.
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Node Aggregates
===============

Node aggregates, like nova's host aggregates for VMs, can be regarded as a mechanism
to further partition an availability zone; while availability zones are visible to
users, node aggregates are only visible to administrators. Allow administrators to
assign key-value pairs to groups of bare metal nodes. Each node can have multiple
aggregates, each aggregate can have multiple key-value pairs, and the same key-value
pair can be assigned to multiple aggregates. This information can be used in the
scheduler to enable advanced scheduling by setting key-value pairs to flavor resource
aggregates field.

Admin users can use the :command:`openstack baremetalcompute aggregate` command to
create, delete and manage aggregates. To see information for this command, run:

.. code-block:: console

    $ openstack baremetalcompute aggregate [TAB]
    add        create     delete     list       list_node  remove     set        show       unset

Availability Zones (AZs)
------------------------

Like Nova, the availability zone is actually a specific metadata attached to
an aggregate. Adding that specific metadata to an aggregate makes the aggregate
visible from an end-user perspective and consequently allows to schedule upon a
specific set of nodes (the ones belonging to the aggregate).

.. note:: One node can be in multiple aggregates, but it can only be in one
  availability zone


Affinity Zones
--------------

The affinity zone is also a specific metadata attached to an aggregate, which
makes server group affinity and anti-affinity happen. You may define it as
failure domains(e.g., by power circuit, rack, room, etc).

.. note:: One node can be in multiple aggregates, but it can only be in one
  affinity zone
