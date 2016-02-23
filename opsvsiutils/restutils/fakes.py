#!/usr/bin/env python
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pytest

from opsvsi.opsvsitest import *

from utils import *


FAKE_PORT_DATA = """
{
    "configuration": {
        "name": "Port-%(index)s",
        "interfaces": ["/rest/v1/system/interfaces/1"],
        "trunks": [413],
        "ip4_address_secondary": ["192.168.1.%(index)s"],
        "lacp": ["active"],
        "bond_mode": ["l2-src-dst-hash"],
        "tag": 654,
        "vlan_mode": "trunk",
        "ip6_address": ["2001:0db8:85a3:0000:0000:8a2e:0370:%(index)04d"],
        "external_ids": {"extid1key": "extid1value"},
        "mac": ["01:23:45:67:89:%(index)02x"],
        "other_config": {"cfg-1key": "cfg1val"},
        "bond_active_slave": "null",
        "ip6_address_secondary": ["2001:0db8:85a3:0000:0000:8a2e:0371:%(index)04d"],
        "ip4_address": "192.168.0.%(index)s",
        "admin": "up",
        "qos_config": {"qos_trust": "none"},
        "ospf_auth_text_key": "null",
        "ospf_auth_type": "null",
        "ospf_if_out_cost": 10,
        "ospf_mtu_ignore": false,
        "ospf_priority": 0,
        "ospf_if_type": "ospf_iftype_broadcast",
        "ospf_intervals": {"transmit_delay": 1}
    },
    "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
}
"""

FAKE_VLAN_DATA = """
{
    "configuration": {
        "name": "%(name)s",
        "id": %(id)s,
        "description": "test_vlan",
        "admin": ["up"],
        "other_config": {},
        "external_ids": {}
    }
}
"""

FAKE_BRIDGE_DATA = """
{
    "configuration": {
        "name": "%s",
        "ports": [],
        "vlans": [],
        "datapath_type": "",
        "other_config": {
            "hwaddr": "",
            "mac-table-size": "16",
            "mac-aging-time": "300"
        },
        "external_ids": {}
     }
}
"""


def create_fake_port(path, switch_ip, port_index):
    data = FAKE_PORT_DATA % {"index": port_index}

    info("\n---------- Creating fake port (%s) ----------\n" %
         port_index)
    info("Testing path: %s\nTesting data: %s\n" % (path, data))

    response_status, response_data = execute_request(path,
                                                     "POST",
                                                     data,
                                                     switch_ip)

    assert response_status == httplib.CREATED, \
        "Response status received: %s\n" % response_status
    info("Fake port \"%s\" created!\n" % port_index)

    assert response_data is "", \
        "Response data received: %s\n" % response_data
    info("Response data: %s\n" % response_data)
    info("---------- Creating fake port (%s) DONE ----------\n" %
         port_index)


def create_fake_vlan(path, switch_ip, fake_vlan_name, vlan_id):
    data = FAKE_VLAN_DATA % {"name": fake_vlan_name, "id": vlan_id}

    info("\n---------- Creating fake vlan (%s) ----------\n" %
         fake_vlan_name)
    info("Testing Path: %s\nTesting Data: %s\n" % (path, data))

    response_status, response_data = execute_request(path,
                                                     "POST",
                                                     data,
                                                     switch_ip)

    assert response_status == httplib.CREATED, \
        "Response status received: %s\n" % response_status
    info("Fake VLAN \"%s\" created!\n" % fake_vlan_name)

    assert response_data is "", \
        "Response data received: %s\n" % response_data
    info("Response data received: %s\n" % response_data)
    info("---------- Creating fake vlan (%s) DONE ----------\n" %
         fake_vlan_name)


def create_fake_bridge(path, switch_ip, fake_bridge_name):
    data = FAKE_BRIDGE_DATA % fake_bridge_name

    info("\n---------- Creating fake bridge (%s) ----------\n" %
         fake_bridge_name)
    info("Testing path: %s\nTesting data: %s\n" % (path, data))

    response_status, response_data = execute_request(path,
                                                     "POST",
                                                     data,
                                                     switch_ip)

    assert response_status == httplib.CREATED, \
        "Response status: %s\n" % response_status
    info("Bridge \"%s\" created!\n" % fake_bridge_name)

    assert response_data is "", \
        "Response data received: %s\n" % response_data
    info("Response data received: %s\n" % response_data)
    info("---------- Creating fake bridge (%s) DONE ----------\n" %
         fake_bridge_name)
