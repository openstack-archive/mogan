# Copyright 2017 Huawei Technologies Co.,LTD.
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
Common parameter types for validating request Body.

"""


name = {
    'type': 'string', 'minLength': 1, 'maxLength': 255,
}


description = {
    'type': ['string', 'null'], 'minLength': 0, 'maxLength': 255,
}


availability_zone = {
    'type': 'string', 'minLength': 1, 'maxLength': 255,
}


image_id = {
    'type': 'string', 'format': 'uuid'
}


network_id = {
    'type': 'string', 'format': 'uuid'
}


network_port_id = {
    'type': 'string', 'format': 'uuid'
}


port_type = {
    'type': 'string', 'minLength': 1, 'maxLength': 255,
}


flavor_id = {
    'type': 'string', 'format': 'uuid'
}


metadata = {
    'type': 'object',
    'patternProperties': {
        '^[a-zA-Z0-9-_:. ]{1,255}$': {
            'type': 'string', 'maxLength': 255
        }
    },
    'additionalProperties': False
}


mac_address = {
    'type': 'string',
    'pattern': '^([0-9a-fA-F]{2})(:[0-9a-fA-F]{2}){5}$'
}


ip_address = {
    'type': 'string',
    'oneOf': [
        {'format': 'ipv4'},
        {'format': 'ipv6'}
    ]
}

personality = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'path': {'type': 'string'},
            'contents': {
                'type': 'string',
                'format': 'base64'
            }
        },
        'additionalProperties': False,
    }
}


boolean = {
    'type': ['boolean', 'string'],
    'enum': [True, 'True', 'TRUE', 'true', '1', 'ON', 'On', 'on',
             'YES', 'Yes', 'yes',
             False, 'False', 'FALSE', 'false', '0', 'OFF', 'Off', 'off',
             'NO', 'No', 'no'],
}


positive_integer = {
    'type': ['integer', 'string'],
    'pattern': '^[0-9]*$', 'minimum': 1
}


flavor_cpus = {
    'type': 'object',
    'patternProperties': {
        'model': {
            'type': 'string', 'maxLength': 255
        },
        'cores': positive_integer,
    },
    'required': ['model', 'cores'],
    'additionalProperties': False
}


flavor_memory = {
    'type': 'object',
    'patternProperties': {
        'type': {
            'type': 'string', 'maxLength': 255
        },
        'size_mb': positive_integer,
    },
    'required': ['type', 'size_mb'],
    'additionalProperties': False
}


flavor_nics = {
    'type': 'array',
    'items': {
        'type': 'object',
        'patternProperties': {
            'type': {
                'type': 'string', 'maxLength': 255
            },
            'speed': {
                'type': 'string', 'maxLength': 255
            },
        },
        'additionalProperties': False,
    },
}


flavor_disks = {
    'type': 'array',
    'items': {
        'type': 'object',
        'patternProperties': {
            'type': {
                'type': 'string', 'maxLength': 255
            },
            'size_gb': positive_integer,
        },
        'additionalProperties': False,
    },
}
