Root disk partitions
--------------------

Mogan supports custom partitions for root disk with partition images, meaning
that users can specify partitions such as root_gb, ephemeral_gb, and swap_mb
when claiming a server. But after the deployment the root partition may not
like what your specified, as the backend driver makes the root partition the
last partition which enables tools like cloud-init's growroot utility to expand
the root partition until the end of the disk.

.. note:: Whole disk images, on the contrary, not support partitions, passing
          partitions to server creation results in a fault and will prevent the
          creation from happening.

#. To create server with partitions, use ``--partition`` parameter on the
:command:`openstack baremetalcompute server create` command.

   For example:

   .. code-block:: console

      $ openstack baremetalcompute server create --image IMAGE --flavor gold \
        --key-name KEY --availability-zone ZONE --partition root_gb=100 \
        --partition ephemeral_gb=200 --partition swap_mb=40960 \
        --nic net-id=UUID SERVER
