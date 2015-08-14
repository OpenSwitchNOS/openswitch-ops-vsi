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
# ex: /usr/bin/sudo <SANDBOX>/build/tmp/sysroots/x86_64-linux/usr/bin/py.test -s example.py

from halonvsi.docker import *
from halonvsi.halon import *
from halonutils.halonutil import *

class CustomTopology( Topo ):
    '''
        This is an example class that shows how to build a custom topology.
        You can customize adding hosts and switches.By using addHost, addSwith
        & addLink methods, you can build custom topologies as shown below.
    '''

    def build(self, hsts=2, sws=1, **_opts):
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
        self.addLink('h2', 's1')

class twoSwitchTest( HalonTest ):

  def setupNet(self):
    # if you override this function, make sure to
    # either pass getNodeOpts() into hopts/sopts of the topology that
    # you build or into addHost/addSwitch calls
    self.net = Mininet(topo=CustomTopology(hsts=2, sws=1,
                                           hopts=self.getHostOpts(),
                                           sopts=self.getSwitchOpts()),
                                           switch=HalonSwitch,
                                           host=HalonHost,
                                           link=HalonLink, controller=None,
                                           build=True)

  def mininet_cli(self):
    CLI(self.net)

class Test_example:

  def setup_class(self):
    # Create the Mininet topology based on mininet.
    Test_example.test = twoSwitchTest()

  # Test for slow routing between directly connected hosts
  def test_mininet_cli(self):
    self.test.mininet_cli()

  def teardown_class(cls):
    # Stop the Docker containers, and
    # mininet topology
    Test_example.test.net.stop()

  def __del__(self):
    del self.test
