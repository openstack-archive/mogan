Server Groups
=============

It's quite like Nova server groups for VMs, but we are based on affinity_zone
which is a special metadata of aggregate. affinity and anti-affinity policies
make sure servers are on the same or different affinity zones.

Create a Server Group
---------------------

#. If you want all servers to run on the same affinity zone, create a group with
`affinity` policy.

   For example:

   .. code-block:: console

      $ openstack baremetalcompute server group create --policy affinity Affi
      +------------+--------------------------------------+
      | Field      | Value                                |
      +------------+--------------------------------------+
      | uuid       | 5ffe7cc8-c793-4568-be3f-654bc9231acd |
      | name       | Affi                                 |
      | user_id    | d4479638a8594d359d7f6115980b08da     |
      | project_id | 378d5add81b44d3e9afc5b99c31ad209     |
      | members    |                                      |
      | policies   | affinity                             |
      +------------+--------------------------------------+

#. If you want all servers to run on different affinity zone, create a group with
`anti-affinity` policy.

   For example:

   .. code-block:: console

      $ openstack baremetalcompute server group create --policy anti-affinity Anti
      +------------+--------------------------------------+
      | Field      | Value                                |
      +------------+--------------------------------------+
      | uuid       | 719d7cf9-141f-4c73-b5e8-669f6b4d4b89 |
      | name       | Anti                                 |
      | user_id    | d4479638a8594d359d7f6115980b08da     |
      | project_id | 378d5add81b44d3e9afc5b99c31ad209     |
      | members    |                                      |
      | policies   | anti-affinity                        |
      +------------+--------------------------------------+

Add a server to Server Group
----------------------------

You can only add a server to a server group when you create the server. Not afterwards.
To add a server to a server group, use the ``--hint group=$group-uuid`` parameter on
the :command:`openstack baremetalcompute server create` command.

   For example:

   .. code-block:: console

      $ openstack baremetalcompute server create --image IMAGE --flavor gold \
        --key-name KEY --hint group=GROUP --nic net-id=UUID SERVER
