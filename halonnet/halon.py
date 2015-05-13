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


class HalonHost ( DockerHost ):
    def __init__( self, name, image = 'mzayats/halon-host', **kwargs ):
        super(HalonHost, self).__init__( name, image, **kwargs )


class HalonLink( DockerLink ):
    def intfName( self, node, n ):
        if isinstance(node, HalonSwitch):
            return repr( n )
        else:
            return super(HalonLink, self).intfName( node, n )

class HalonSwitch ( DockerNode, Switch ):
    def __init__( self, name, image = 'mzayats/dockered-ovs', numPorts = 8, **kwargs ):
        super( HalonSwitch, self).__init__( name, image, **kwargs )
        self.inNamespace = True
        self.numPorts = numPorts

    def start( self, controllers ):
        self.cmd("ip netns add swns")
        for i in range(1, self.numPorts + 1):
            if str(i) not in self.nameToIntf:
                self.cmd("ip netns exec swns ip tuntap add dev " + str(i) + " mode tap")
            else:
                self.cmd("ip link set dev " + str(i) + " netns swns up")
        self.cmd("ovsdb-tool create")
        self.cmd("ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock --detach")
        self.cmd("ip netns exec swns ovs-vswitchd --detach")
        self.cmd("ovs-vsctl add-br br0")
        self.cmd("ovs-vsctl set bridge br0 datapath_type=netdev")

    def stop( self, deleteIntfs = True ):
        pass

class HalonTest:
    def __init__(self):
        parser = argparse.ArgumentParser()
        self.regArgs(parser)
        args = parser.parse_args()
        self.procArgs(args)
        self.setLogLevel()
        self.setupNet()

    def setLogLevel(self, levelname='info'):
        setLogLevel(levelname)

    def setupNet(self):
        self.net = Mininet( topo=SingleSwitchTopo(k=2), switch=HalonSwitch,
                            host=HalonHost, link=HalonLink, controller=None,
                            build=True )
    def regArgs(self, parser):
        parser.add_argument("--id", 
            help="Specify numeric test ID, default is process ID", type=int)

    def procArgs(self, args):
        if args.id:
            self.id=args.id
        else:
            self.id=os.getpid()

    def error(self):
        error('=====\n')
        error('=====  ERROR: test outputs can be found in ' + '/tmp/halontests/' + str(self.id) + ' =====\n')
        error('=====\n')

    def success(self):
        info('=====\n') 
        info('=====  SUCCESS: test outputs can be found in ' + '/tmp/halontests/' + str(self.id) + ' =====\n')
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
