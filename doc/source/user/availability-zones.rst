====================================================
Select availability zones where servers are launched
====================================================

You can select which availability zone servers are launched on.

#. To select the availability zone where servers are launched, use the
   ``--availability-zone ZONE`` parameter on the :command:`openstack
   baremetalcompute server create` command.

   For example:

   .. code-block:: console

      $ openstack baremetalcompute server create --image IMAGE --flavor m1.tiny \
        --key-name KEY --availability-zone ZONE --nic net-id=UUID \
        --partition ephemeral_gb=500 SERVER

#. To view the list of valid zones, use the :command:`openstack baremetalcompute
   availability zone list` command.

   .. code-block:: console

      $ openstack baremetalcompute availability zone list
      +-----------+
      | Zone Name |
      +-----------+
      | zone1     |
      | zone2     |
      +-----------+
