#!/usr/bin/python

from mininet.net import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import *
from mininet.topo import *
from docker import *
from subprocess import *
from subprocess import *
import shutil
import select
import re
import argparse
import os

SWNS_EXEC = '/sbin/ip netns exec swns '

class HalonHost (DockerHost):
    def __init__(self, name, image='ubuntu:latest', **kwargs):
        super(HalonHost, self).__init__(name, image, **kwargs)


class HalonLink(DockerLink):
    def intfName(self, node, n):
        if isinstance(node, HalonSwitch):
            return repr(n)
        else:
            return super(HalonLink, self).intfName(node, n)


class HalonSwitch (DockerNode, Switch):
    def __init__(self, name, image='openhalon/genericx86-64',
                 numPorts=5, **kwargs):
        super(HalonSwitch, self).__init__(name, image, **kwargs)

        # Wait until the OVSDB is up in the Halon switch.
        self.cmd("while true; do \
                      /usr/bin/ovsdb-client dump 1>/dev/null 2>&1; \
                      (( $? == 0 )) && break; \
                 done")

        self.inNamespace = True
        self.numPorts = numPorts

    def start(self, controllers):
        # Create TUN tap interfaces.
        # Mininet would have created as many interfaces
        # as the number of the hosts defined in the TOPO.
        # Create the rest as TUN TAP interfaces
        # in 'swns' namespace.
        for i in range(1, self.numPorts + 1):
            if str(i) not in self.nameToIntf:
                self.cmd(SWNS_EXEC + "/sbin/ip tuntap add dev " + str(i) + " mode tap")

        # Move the interfaces created by Mininet to swns namespace.
        for intf in self.nameToIntf:
            if intf == 'lo':
                continue
            self.cmd("/sbin/ip link set " + intf + " netns swns")
            self.swns_cmd("/sbin/ip link set " + intf + " up")

    def startShell(self):
        DockerNode.startShell(self)
        self.cmd("ip link set dev eth0 down")
        self.cmd("ip link set dev eth0 name mgmt")
        self.cmd("ip link set dev mgmt up")

    def stop(self, deleteIntfs=True):
        pass

    def swns_cmd(self, cmd):
        return self.cmd(SWNS_EXEC + cmd)


class HalonTest:
    def __init__(self, test_id=None, switchmounts=[], hostmounts=[], start_net=True):
        # If 'test_id' is not passed use PID as the testid
        if test_id is None:
            test_id = str(os.getpid())

        self.id = test_id
        self.switchmounts = switchmounts
        self.hostmounts = hostmounts

        self.testdir = "/tmp/halon-test/" + self.id
        shutil.rmtree(self.testdir, ignore_errors=True)
        os.makedirs(self.testdir)
        info("Test log dir: " + self.testdir)

        # Set log level to 'debug' to enable Debugging.
        self.setLogLevel('info')

        # Setup and start the network topology.
        if start_net is True:
            self.setupNet()
            self.net.start()

    def setLogLevel(self, levelname='info'):
        setLogLevel(levelname)

    def getNodeOpts(self):
        return {'testid': self.id, 'testdir': self.testdir}

    def getHostOpts(self):
        opts = self.getNodeOpts()
        opts.update({'mounts':self.hostmounts})
        return opts

    def getSwitchOpts(self):
        opts = self.getNodeOpts()
        opts.update({'mounts':self.switchmounts})
        return opts

    def stopNet(self):
        self.net.stop()

    def setupNet(self):
        # If you override this function, make sure to pass
        # Host/Switch options into hopts/sopts of the topology that
        # you build or into addHost/addSwitch calls
        topo = SingleSwitchTopo(k=2,
                                hopts=self.getHostOpts(),
                                sopts=self.getSwitchOpts())

        self.net = Mininet(topo,
                           switch=HalonSwitch,
                           host=HalonHost,
                           link=HalonLink,
                           controller=None,
                           build=True)
