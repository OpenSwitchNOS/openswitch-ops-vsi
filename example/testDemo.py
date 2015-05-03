#!/usr/bin/python

from mininet.net import * 
from mininet.topo import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import * 
from subprocess import *
from subprocess import *
from halonnet.docker import * 
from halonnet.halon import * 
import select

class demoTest( HalonTest ):
    def test(self):
        s1 = self.net.switches[ 0 ]

        info( 'Bridging ports 1 and 2\n')
        #configuring Halon, in the future it would be through
        #proper Halon commands
        s1.cmd("ovs-vsctl add-port br0 1 -- add-port br0 2")
        s1.cmd("ip netns exec swns iptables -A INPUT -i 1 -j DROP")
        s1.cmd("ip netns exec swns iptables -A INPUT -i 2 -j DROP")
        s1.cmd("ip netns exec swns iptables -A FORWARD -i 1 -j DROP")
        s1.cmd("ip netns exec swns iptables -A FORWARD -i 2 -j DROP")

        info( '*** Running ping test between all hosts\n')
        ret = self.net.pingAll()
        #return code means whether the test is successful 
        if ret > 0:
            return False
        else:
            return True
             

if __name__ == '__main__':
    test = demoTest()
    test.run(runCLI=False) 
