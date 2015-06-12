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
    pw = os.getcwd()
    test = demoTest(id='arg-test',
                    switchmounts=[pw + "/printme.sh:/printme.sh"],
                    hostmounts=[pw +"/printme.sh:/printme.sh"])
    test.test()

    # Set runCLI to true to debug test failures.
    runCLI=False
    if runCLI is True:
        CLI(test.net)
