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
Main abstraction layer for retrieving and storing information about disk
images used by the compute layer.
"""

from mogan.image import glance


class API(object):
    """Responsible for exposing a relatively stable internal API for other
    modules in Mogan to retrieve information about disk images.

    """

    def get(self, context, image_id):
        """Retrieves the information record for a single disk image.

        :param context: The context object for the request
        :param image_uuid: A UUID identifier to look up image information for.
        """
        session = glance.get_image_service(context)
        return session.show(context, image_id)
