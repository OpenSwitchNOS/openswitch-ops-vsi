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

import json
import httplib
import random
import urllib
import ssl
import os
import time
import pytest
import subprocess

from opsvsi.opsvsitest import *
from copy import deepcopy

PORT_DATA = {
    "configuration": {
        "name": "Port1",
        "interfaces": ["/rest/v1/system/interfaces/1"],
        "trunks": [413],
        "ip4_address_secondary": ["192.168.1.1"],
        "lacp": "active",
        "bond_mode": "l2-src-dst-hash",
        "tag": 654,
        "vlan_mode": "trunk",
        "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "external_ids": {"extid1key": "extid1value"},
        "mac": "01:23:45:67:89:ab",
        "other_config": {"cfg-1key": "cfg1val"},
        "bond_active_slave": "null",
        "ip6_address_secondary": ["01:23:45:67:89:ab"],
        "ip4_address": "192.168.0.1",
        "admin": "up",
        "ospf_auth_text_key": "null",
        "ospf_auth_type": "null",
        "ospf_if_out_cost": 10,
        "ospf_if_type": "ospf_iftype_broadcast",
        "ospf_intervals": {"transmit_delay": 1},
        "ospf_mtu_ignore": False,
        "ospf_priority": 0,
    },
    "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
}

LOGIN_URI = '/login'
ACCOUNT_URI = "/account"
DEFAULT_USER = 'netop'
DEFAULT_PASSWORD = 'netop'


def get_container_id(switch):
    container_name = switch.testid + "_" + switch.name
    container_id = subprocess.check_output(["docker", "ps", "-a",
                                           "-q", "-f", "name=" +
                                           container_name]).strip()
    return container_id


def get_switch_ip(switch):
    switch_ip = switch.cmd("python -c \"import socket; \
                           print socket.gethostbyname(socket.gethostname())\"")
    switch_ip = switch_ip.rstrip("\r\n")
    return switch_ip


def create_test_port(ip):
    cookie_header = login(ip)
    path = "/rest/v1/system/ports"
    status_code, response_data = execute_request(path,
                                                 "POST",
                                                 json.dumps(PORT_DATA),
                                                 ip, xtra_header=cookie_header)
    return status_code, response_data


def update_test_field(switch_ip, path, field, new_value):
    cookie_header = login(switch_ip)
    """
    Update field from existing table:
        - Perform a GET request to an existing path defined in path
        - Retrieve Configuration section
        - Update field with new_value
        - Perform a PUT request
    """
    status_code, response_data = execute_request(path,
                                                 "GET",
                                                 None,
                                                 switch_ip,
                                                 xtra_header=cookie_header)

    assert status_code is httplib.OK, \
        "Wrong status code, received: %s\n" % status_code
    assert response_data is not "", \
        "Response data received: %s\n" % response_data

    json_data = {}

    try:
        json_data = json.loads(response_data)
    except:
        assert False, "Malformed JSON"

    port_info = {}
    port_info["configuration"] = json_data["configuration"]

    # update value
    port_info["configuration"][field] = new_value

    status_code, response_data = execute_request(path,
                                                 "PUT",
                                                 json.dumps(port_info),
                                                 switch_ip,
                                                 xtra_header=cookie_header)
    assert status_code == httplib.OK, \
        "Wrong status code, received: %s\n" % status_code
    assert response_data is "", \
        "Response data received: %s\n" % response_data


def compare_dict(dict1, dict2):
    if dict1 is None or dict2 is None:
        return False

    if type(dict1) is not dict or type(dict2) is not dict:
        return False

    shared_keys = set(dict2.keys()) & set(dict2.keys())

    if not (len(shared_keys) == len(dict1.keys()) and
            len(shared_keys) == len(dict2.keys())):
        return False

    dicts_are_equal = True
    for key in dict1.keys():
        if type(dict1[key]) is dict:
            dicts_are_equal = dicts_are_equal and compare_dict(dict1[key],
                                                               dict2[key])
        elif type(dict1[key]) is list:
            intersection = set(dict1[key]) ^ set(dict2[key])
            dicts_are_equal = dicts_are_equal and len(intersection) == 0
        else:
            dicts_are_equal = dicts_are_equal and (dict1[key] == dict2[key])

    return dicts_are_equal


def execute_port_operations(data, port_name, http_method, operation_uri,
                            switch_ip):
    cookie_header = login(switch_ip)

    results = []

    for attribute in data:

        attribute_name = attribute[0]
        attribute_value = attribute[1]
        expected_code = attribute[2]

        request_data = deepcopy(PORT_DATA)
        request_data['configuration']['name'] = \
            "{0}_{1}_{2}".format(port_name, attribute_name, expected_code)

        if http_method == 'PUT':

            # Create a test port
            status_code, response_data = \
                execute_request(operation_uri, "POST",
                                json.dumps(request_data), switch_ip,
                                xtra_header=cookie_header)

            if status_code != httplib.CREATED:
                return []

            port_uri = operation_uri + "/%s" % \
                request_data['configuration']['name']

            # Delete reference_by from PUT
            del request_data['referenced_by']
        else:
            port_uri = operation_uri

        # Execute request

        print "Attempting to {0} a port with value '{1}' ({3}) for attribute \
               '{2}'".format(http_method, attribute_value, attribute_name,
                             type(attribute_value).__name__)
        # Change value for specified attribute
        request_data['configuration'][attribute_name] = attribute_value
        # Execute request
        status_code, response_data = execute_request(port_uri,
                                                     http_method,
                                                     json.dumps(request_data),
                                                     switch_ip,
                                                     xtra_header=cookie_header)

        # Check if status code was as expected

        if status_code != expected_code:
            results.append((attribute_name, False, status_code))
        else:
            results.append((attribute_name, True, status_code))

    return results


def execute_request(path, http_method, data, ip, full_response=False,
                    xtra_header=None):

    url = path.replace(';', '&')

    headers = {"Content-type": "application/json", "Accept": "text/plain"}
    if xtra_header:
        headers.update(xtra_header)

    sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sslcontext.verify_mode = ssl.CERT_REQUIRED
    sslcontext.check_hostname = False
    src_path = os.path.dirname(os.path.realpath(__file__))
    src_file = os.path.join(src_path, 'server.crt')
    sslcontext.load_verify_locations(src_file)
    conn = httplib.HTTPSConnection(ip, 443, context=sslcontext)
    conn.request(http_method, url, data, headers)
    response = conn.getresponse()
    status_code, response_data = response.status, response.read()
    conn.close()

    if full_response:
        return response, response_data
    else:
        return status_code, response_data


def create_test_ports(ip, num_ports):
    cookie_header = login(ip)
    path = "/rest/v1/system/ports"

    data = deepcopy(PORT_DATA)
    for port in range(num_ports):
        data["configuration"]["name"] = "Port%s" % port
        status_code, response_data = execute_request(
            path, "POST", json.dumps(data), ip, xtra_header=cookie_header)

        if status_code != httplib.CREATED:
            return status_code

    return httplib.CREATED


def query_object(switch_ip, path):
    """
    Query a port
    """
    status_code, response_data = execute_request(path, "GET", None, switch_ip)
    assert status_code == httplib.OK, "Wrong status code %s " % status_code

    assert response_data is not None, "Response data is empty"

    json_data = {}
    try:
        json_data = json.loads(response_data)
    except:
        assert False, "Malformed JSON"

    return json_data


def fill_with_function(f, n):
    list = [f for i in xrange(n)]
    return list


def random_mac():
    random.seed()
    mac = "%02x:%02x:%02x:%02x:%02x:%02x" % (random.randint(0, 255),
                                             random.randint(0, 255),
                                             random.randint(0, 255),
                                             random.randint(0, 255),
                                             random.randint(0, 255),
                                             random.randint(0, 255))
    return mac


def random_ip6_address():
    random.seed()
    ipv6 = ':'.join('{:x}'.format(random.randint(0, 2 ** 16 - 1))
                    for i in range(8))
    return ipv6


def login(switch_ip, username=None, password=None):
    '''
    Common function to login the user into the system.
    Optionally takes username and/or password, otherwise
    the default user and password from ops_netop group
    is used.
    Returns the Cookie header.
    '''

    # Force to provide a password if a username is provided
    if username is not None:
        assert password is not None, "Must provide password for Login"

    # Initialize parameters

    if not username:
        username = DEFAULT_USER
    if not password:
        password = DEFAULT_PASSWORD

    params = {'username': username,
              'password': password}
    _headers = {"Content-type": "application/x-www-form-urlencoded",
                "Accept": "text/plain"}

    # Attempt Login
    response, response_data = execute_request(LOGIN_URI, "POST",
                                              urllib.urlencode(params),
                                              switch_ip, True, _headers)
    assert response.status == httplib.OK, ("Login POST not successful, " +
                                           "code: %s " % response.status)
    # Get cookie header
    cookie_header = {'Cookie': response.getheader('set-cookie')}

    # Verify Login was successful
    status_code, response_data = execute_request(LOGIN_URI, "GET", None,
                                                 switch_ip, False,
                                                 cookie_header)
    assert status_code == httplib.OK, ("Login GET not successful, " +
                                       "code: %s " % status_code)

    return cookie_header


def get_json(response_data):
    json_data = {}
    try:
        json_data = json.loads(response_data)
    except:
        assert False, "Malformed JSON"

    return json_data


def validate_keys_complete_object(json_data):
    assert json_data["configuration"] is not None, \
        "configuration key is not present"
    assert json_data["statistics"] is not None, \
        "statistics key is not present"
    assert json_data["status"] is not None, "status key is not present"

    return True


def rest_sanity_check(switch_ip):
    cookie_header = login(switch_ip)
    info("Cookie Header" + str(cookie_header))
    info("\nSwitch Sanity Check: Verify if System table row and bridge_normal \
        exist\n")
    # Check if bridge_normal is ready, loop until ready or timeout finish
    system_path = "/rest/v1/system"
    bridge_path = "/rest/v1/system/bridges/bridge_normal"
    count = 1
    max_retries = 60  # 1 minute
    while count <= max_retries:
        info("\nSwitch Sanity Check: Try count %d \n" % count)
        try:
            status_system, response_system = \
                execute_request(system_path, "GET", None, switch_ip, xtra_header = cookie_header)
            status_bridge, response_bridge = \
                execute_request(bridge_path, "GET", None, switch_ip, xtra_header = cookie_header)

            if status_system is httplib.OK and \
                    response_system is not None and \
                    status_bridge is httplib.OK and \
                    response_bridge is not None:
                break
        except:
            pass

        count += 1
        info("\nSwitch Sanity Check: Retrying\n")
        time.sleep(1)

    assert count <= max_retries, "Switch Sanity check failure: After waiting \
        %d seconds, the switch is still not ready to run the tests" \
        % max_retries
