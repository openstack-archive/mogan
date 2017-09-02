Root disk partitions
--------------------

Mogan supports custom partitions for root disk with partition images, meaning
that users can specify partitions such as root_gb, ephemeral_gb, and swap_mb
when claiming a server. But after the deployment the root partition may not
like what your specified, as the backend driver makes the root partition the
last partition which enables tools like cloud-init's growroot utility to expand
the root partition until the end of the disk.

.. note:: Whole disk images, on the contrary, not support partitions, and will
          raise errors if specifying partitions when claiming servers.
