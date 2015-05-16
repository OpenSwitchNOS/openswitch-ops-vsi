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
    def setupNet(self):
        self.net = Mininet(switch=HalonSwitch, host=HalonHost)

        self.s1 = self.net.addSwitch('s1', **self.getSwitchOpts())
        self.h1 = self.net.addHost('h1', **self.getHostOpts())

    def test(self):
        s1result = self.s1.cmd("sh /printme.sh")
        h1result = self.h1.cmd("sh /printme.sh")

        if s1result == "SUCCESS" and h1result == "SUCCESS":
            return True
        else:
            return False


if __name__ == '__main__':
    test = demoTest()
    test.run(runCLI=False)
