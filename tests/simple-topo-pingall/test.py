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

class demoTest( HalonTest ):

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
        h1 = self.net.hosts[ 0 ]

        # Assign IP address to a switch interface to test
        # connectivity between switch and host1
        out = s1.swns_cmd("ifconfig 1 10.0.0.10 netmask 255.0.0.0")

        info( '*** Running ping test between host-server\n')
        ret = h1.cmd("ping -c 1 10.0.0.10")

        sent, received = demoTest._parsePing(ret)

        #return code means whether the test is successful
        print sent
        if sent == received:
            return True
        else:
            return False


if __name__ == '__main__':

    # Create a test topology, and start it
    test = demoTest()

    # Run all the tests sequentially here.
    test.test()

    # Set runCLI to true to debug test failures.
    runCLI=False
    if runCLI is True:
        CLI(test.net)
