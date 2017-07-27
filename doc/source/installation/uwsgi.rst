..
      Copyright (c) 2017 Intel Corporation
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


Running Mogan API using uWSGI
=============================
The recommended way to deploy Mogan is have a web server such as Apache
or nginx to handle http requests and proxy these requests to Mogan WSGI
app running in uWSGI. Mogan comes with some configuration templates on
how to deploy the api service with Apache and uWSGI.

app.wsgi
********
The ``mogan/api/app.wsgi`` file contains a WSGI application of
Mogan API service. This file is installed with Mogan application
code.

apache-mogan.template
*********************
The ``mogan/etc/apache-mogan.template`` file contains a copy
of Apache configuration file for Mogan API used by devstack.

mogan-uwsgi.ini.sample
**********************
The ``mogan/etc/mogan-uwsgi.ini.sample`` file is a sample
configuration file for uWSGI server. Update the file to match your
system configuration.

Steps to use these sample configuration files:

1. Enable mod_proxy_uwsgi module

* On Ubuntu install required uwsgi package
  ``sudo apt-get install libapache2-mod-proxy-uwsgi``; enable using
  ``sudo a2enmod proxy``, ``sudo a2enmod proxy_uwsgi``.
* On Fedora the required package is mod_proxy_uwsgi; enable by creating a file
  ``/etc/httpd/conf.modules.d/11-proxy_uwsgi.conf`` containing
  ``LoadModule proxy_uwsgi_module modules/mod_proxy_uwsgi.so``

2. On deb-based systems copy or symlink the file ``apache-mogan.template`` to
  ``/etc/apache2/sites-available/mogan.conf``. For rpm-based systems the file
  should go into ``/etc/httpd/conf.d/mogan.conf``.
  uWSGI need a socket file to connect between apache proxy and uWSGI web
  server, but ``/var/run`` will be empty on after reboot, so we can use
  systemd-temptiles to automatically create a socket_dir::

    sudo mkdir -p /etc/tmpfiles.d/
    echo "d /var/run/uwsgi 0755 $STACK_USER root" | sudo tee /etc/tmpfiles.d/uwsgi.conf
    sudo systemd-tmpfiles --create /etc/tmpfiles.d/uwsgi.conf

3. Enable Mogan site. On deb-based systems::

      $ a2ensite mogan
      $ service apache2 reload

   On rpm-based systems::

      $ service httpd reload

4. Copy mogan/etc/mogan-uwsgi.ini.sample to /etc/mogan/mogan-uwsgi.ini.

5. Start Mogan api using uWSGI::

      $ sudo pip install uwsgi
      $ uwsgi --ini /etc/mogan/mogan-uwsgi.ini
