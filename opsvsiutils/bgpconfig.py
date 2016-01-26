#!/usr/bin/python

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

from opsvsi.opsvsitest import *
from opsvsiutils.systemutil import *
from opsvsi.quagga import *

# Flags for defining what types of switches will be used for BGP testing.
# The "peer" is only applicable to tests that have more than one switch
# emulated
enableOpenSwitch = True
enablePeerOpenSwitch = True


def getSwitchType(isOps):
    if isOps:
        return VsiOpenSwitch
    else:
        return QuaggaSwitch

SWITCH_TYPE = getSwitchType(enableOpenSwitch)
PEER_SWITCH_TYPE = getSwitchType(enablePeerOpenSwitch)


class BgpConfig(object):
    def __init__(self, asn, routerid, network):
        self.neighbors = []
        self.networks = []
        self.routeMaps = []
        self.prefixLists = []

        self.asn = asn
        self.routerid = routerid

        self.addNetwork(network)

    def addNeighbor(self, neighbor):
        self.neighbors.append(neighbor)

    def addNetwork(self, network):
        self.networks.append(network)

    def addRouteMap(self, neighbor, prefix_list, dir, action='', metric='',
                    community=''):
        self.routeMaps.append([neighbor, prefix_list, dir, action,
                               metric, community])


# Prefix-list configurations
class PrefixList(object):
    def __init__(self, name, seq_num, action, network, prefixLen):
        self.name = name
        self.seq_num = seq_num
        self.action = action
        self.network = network
        self.prefixLen = prefixLen
