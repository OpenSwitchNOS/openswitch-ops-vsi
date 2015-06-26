#!/usr/bin/env python

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

# This script is used as a virtual test setup. By using this script,
# or modifying it as required, developers can quickly build topologies
# and test their changes on their VMs.
# Pre-requisites:
# 1. Checkout the halon-vsi repo.
# 2. Run 'make devenv_ct_init'.
# 3. Export the Halon docker image of the switch from your build directory.

# To run this file, we have to point to the native python inside the sandbox.
# ex: /usr/bin/sudo <SANDBOX>/build/tmp/sysroots/x86_64-linux/usr/bin/python-native/python2.7 example.py

import os
import sys
import time
import subprocess
from halonvsi.docker import *
from halonvsi.halon import *

class CustomTopology( Topo ):
    '''
        This is an example class that shows how to build a custom topology.
        You can customize adding hosts and switches.By using addHost, addSwith
        & addLink methods, you can build custom topologies as shown below.
    '''

    def build(self, hsts=2, sws=2, **_opts):
        '''Function to build the custom topology of two hosts and two switches'''
        self.hsts = hsts
        self.sws = sws
        #Add list of hosts
        for h in irange( 1, hsts):
            host = self.addHost('h%s' % h)
        #Add list of switches
        for s in irange(1, sws):
            switch = self.addSwitch('s%s' % s)
        #Add links between nodes based on custom topology
        self.addLink('h1', 's1')
        self.addLink('h2', 's2')
        self.addLink('s1', 's2')

def topology():
    # We can use different types of switches such as 'Switch', 'OVSSwitch'
    # which come in built with Mininet. Shown below is the 'HalonSwitch' class
    # with default configuration. For 'HalonSwitch', we can pass arguments
    # to mention specific docker images.
    # ex: switch = HalonSwitch(image="my_switch_image")
    switch = HalonSwitch

    # We can use the default 'Host' class from Mininet or use the HalonHost class
    # For 'HalonHost', we can mention specific images.
    # ex. host = HalonHost(image="my_host_image")
    host = HalonHost

    # There are no options as of now to modify HalonLink. DO NOT use the default Link
    # class from Mininet.
    link = HalonLink

    # We can also pass options to the host/switch using the two variables below.
    # Shown below is creating a directory to store test output.
    test_id = str(os.getpid())
    testdir = "/tmp/halon-test/" + test_id
    os.makedirs(testdir)
    print "Test log dir: " + testdir + "\n"
    my_hopts = {'testid': test_id, 'testdir': testdir}
    my_sopts = {'testid': test_id, 'testdir': testdir}

    # Shown below is the default topology with two switches and two hosts.
    # Edit the CustomTopology class above to build your own.
    net = Mininet(topo=CustomTopology(hsts=2, sws=2
                                      hopts=my_hopts,
                                      sopts=my_sopts),
                                      switch=HalonSwitch,
                                      host=HalonHost,
                                      link=HalonLink, controller=None,
                                      build=True)

    # Mininet also has a list of standard topologies like SingleSwitchReversedTopo,
    # LinearTopo, MultiGraph and so on. Refer to Mininet Doxygen documentation for details.
    # Uncomment the line below for using Mininet's standard topology.
    '''net = Mininet(topo=SingleSwitchTopo(k=2,
                                        hopts=my_hopts,
                                        sopts=my_sopts),
                                        switch=HalonSwitch,
                                        host=HalonHost,
                                        link=HalonLink, controller=None,
                                        build=True)'''
    return net

if __name__ == '__main__':
    print "#################################### Halon Sample Script #########################\n"
    print "example.py: This is a sample python script which represents a Virtual Test Platform\n"
    net = topology()
    net.start()
    CLI(net)
    net.stop()
