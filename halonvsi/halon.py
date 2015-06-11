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
        # Create TUN tap interface.
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
    def __init__(self):
        parser = argparse.ArgumentParser()
        self.regArgs(parser)
        args = parser.parse_args()
        self.procArgs(args)

        self.testdir = "/tmp/halon-test/" + self.id
        os.makedirs(self.testdir)

        self.setLogLevel()

        # Enable the following line to enable Debugging.
        # self.setLogLevel('debug')

        self.setupNet()

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

    def setupNet(self):
        # if you override this function, make sure to
        # either pass getNodeOpts() into hopts/sopts of the topology that
        # you build or into addHost/addSwitch calls
        self.net = Mininet(topo=SingleSwitchTopo(
            k=2,
            hopts=self.getHostOpts(),
            sopts=self.getSwitchOpts()),
            switch=HalonSwitch,
            host=HalonHost,
            link=HalonLink, controller=None,
            build=True)

    def regArgs(self, parser):
        parser.add_argument(
            "-i", "--id", default=os.getpid(),
            help="Specify numeric test ID, default is process ID", type=int)
        parser.add_argument(
            "--sm", "--switchmount", action="append", dest="switchmounts",
            default=[], metavar="localpath:switchpath",
            help="mount local file or directory into the \
                  specified path in all the switches")
        parser.add_argument(
            "--hm", "--hostmount", action="append", dest="hostmounts",
            default=[], metavar="localpath:hostpath",
            help="mount local file or directory into the \
                  specified path in all the hosts")


    def procArgs(self, args):
        self.id = str(args.id)
        self.switchmounts = args.switchmounts
        self.hostmounts = args.hostmounts

    def error(self):
        error('=====\n')
        error('===== ERROR: test outputs can be found in ' +
              self.testdir + '\n')
        error('=====\n')

    def success(self):
        info('=====\n')
        info('===== SUCCESS: test outputs can be found in ' +
             self.testdir + '\n')
        info('=====\n')

    def run(self, runCLI=False):
        self.net.start()
        if self.test():
            self.success()
        else:
            self.error()
        if runCLI:
            CLI(self.net)
        self.net.stop()

    def test(self):
        pass
