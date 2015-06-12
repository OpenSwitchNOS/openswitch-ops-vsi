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
from halonvsi.docker import *
from halonvsi.halon import *
import select

class myTopo( Topo ):
    """Custom Topology Example
    H1[h1-eth0]<--->[1]S1[2]<--->[2]S2[1]<--->[h2-eth0]H2
    """

    def build(self, hsts=2, sws=2, **_opts):
        self.hsts = hsts
        self.sws = sws

        "add list of hosts"
        for h in irange( 1, hsts):
            host = self.addHost( 'h%s' % h)

        "add list of switches"
        for s in irange(1, sws):
            switch = self.addSwitch( 's%s' %s)

        "Add links between nodes based on custom topo"
        self.addLink('h1', 's1')
        self.addLink('h2', 's2')
        self.addLink('s1', 's2')

class demoTest( HalonTest ):

    """override the setupNet routine to craete custom Topo.
    pass the global variables switch,host,link to mininet topo
    as HalonSwitch,HalonHost,HalonLink
    """

    def setupNet(self):
        self.net = Mininet(topo=myTopo(hsts=2, sws=2,
                                       hopts=self.getHostOpts(),
                                       sopts=self.getSwitchOpts()),
                           switch=HalonSwitch,
                           host=HalonHost,
                           link=HalonLink, controller=None,
                           build=True)

    @staticmethod
    def _parsePing( pingOutput ):
        "Parse ping output and return packets sent, received."
        # Check for downed link
        if 'connect: Network is unreachable' in pingOutput:
            return (1, 0)
        r = r'(\d+) packets transmitted, (\d+) received'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return (1, 0)
        sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
        return sent, received

    def test(self):
        s1 = self.net.switches[ 0 ]
        s2 = self.net.switches[ 1 ]
        h1 = self.net.hosts[ 0 ]
        h2 = self.net.hosts[ 1 ]

        #configuring Halon, in the future it would be through
        #proper Halon commands

        h1.cmd("ifconfig h1-eth0 10.0.10.1 netmask 255.255.255.0 up")
        h2.cmd("ifconfig h2-eth0 10.0.30.1 netmask 255.255.255.0 up")

        s1.swns_cmd("ifconfig 1 10.0.10.2 netmask 255.255.255.0 up")
        s1.swns_cmd("ifconfig 2 10.0.20.1 netmask 255.255.255.0 up")
        s2.swns_cmd("ifconfig 2 10.0.20.2 netmask 255.255.255.0 up")
        s2.swns_cmd("ifconfig 1 10.0.30.2 netmask 255.255.255.0 up")

        #Add route on S1 and S2
        s1.swns_cmd("route add -net 10.0.30.0 netmask 255.255.255.0 gw 10.0.20.2")
        s2.swns_cmd("route add -net 10.0.10.0 netmask 255.255.255.0 gw 10.0.20.1")

        #Add default gateway in host
        h1.cmd("route add default gw 10.0.10.2")
        h2.cmd("route add default gw 10.0.30.2")

        info( '*** Running ping test between host1-sw1-sw2-host2\n')
        ret = h1.cmd("ping -c 1 10.0.30.1")
        print ret

        sent, received = demoTest._parsePing(ret)

        #return code means whether the test is successful
        print sent
        if sent == received:
            return True
        else:
            return False


if __name__ == '__main__':

    # Create a test topology.
    test = demoTest()

    # Run all the tests sequentially.
    test.test()

    # Set runCLI to true to debug test failures.
    runCLI=False
    if runCLI is True:
        CLI(test.net)
