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


class HalonHost (DockerHost):
    def __init__(self, name, image='mzayats/halon-host', **kwargs):
        super(HalonHost, self).__init__(name, image, **kwargs)


class HalonLink(DockerLink):
    def intfName(self, node, n):
        if isinstance(node, HalonSwitch):
            return repr(n)
        else:
            return super(HalonLink, self).intfName(node, n)


class HalonSwitch (DockerNode, Switch):
    def __init__(self, name, image='mzayats/dockered-ovs',
                 numPorts=8, **kwargs):
        super(HalonSwitch, self).__init__(name, image, **kwargs)
        self.inNamespace = True
        self.numPorts = numPorts

    def start(self, controllers):
        self.cmd("ip netns add swns")
        for i in range(1, self.numPorts + 1):
            if str(i) not in self.nameToIntf:
                self.cmd("ip netns exec swns ip tuntap add dev "
                         + str(i) + " mode tap")
            else:
                self.cmd("ip link set dev " + str(i) + " netns swns up")
        self.cmd("ovsdb-tool create")
        self.cmd("ovsdb-server --remote=punix:/usr/local/var/" +
                 "run/openvswitch/db.sock --detach")
        self.cmd("ip netns exec swns ovs-vswitchd --detach")
        self.cmd("ovs-vsctl add-br br0")
        self.cmd("ovs-vsctl set bridge br0 datapath_type=netdev")

    def stop(self, deleteIntfs=True):
        pass


class HalonTest:
    def __init__(self):
        parser = argparse.ArgumentParser()
        self.regArgs(parser)
        args = parser.parse_args()
        self.procArgs(args)

        self.testdir = "/tmp/halonnet/" + self.id
        os.makedirs(self.testdir)

        self.setLogLevel()
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
