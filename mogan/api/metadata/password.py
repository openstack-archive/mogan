# Copyright 2012 Nebula, Inc.
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

from six.moves import range

CHUNKS = 4
CHUNK_LENGTH = 255
MAX_SIZE = CHUNKS * CHUNK_LENGTH


# TODO(ShaoHe), need to store password in system_metadata
def extract_password(password):
    return password or None


def convert_password(context, password):
    """Stores password as system_metadata items.

    Password is stored with the keys 'password_0' -> 'password_3'.
    """
    password = password or ''
    meta = {}
    for i in range(CHUNKS):
        meta['password_%d' % i] = password[:CHUNK_LENGTH]
        password = password[CHUNK_LENGTH:]
    return meta
