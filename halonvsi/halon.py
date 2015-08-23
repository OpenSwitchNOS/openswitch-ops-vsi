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
import uuid

SWNS_EXEC = '/sbin/ip netns exec swns '

class HalonHost (DockerHost):
    def __init__(self, name, **kwargs):
        kwargs['nodetype'] = "HalonHost"

        image = kwargs.pop('HostImage')
        super(HalonHost, self).__init__(name, image, **kwargs)


class HalonLink(DockerLink):
    def intfName(self, node, n):
        if isinstance(node, HalonSwitch):
            return repr(n)
        else:
            return super(HalonLink, self).intfName(node, n)


class HalonSwitch (DockerNode, Switch):
    def __init__(self, name, image='openswitch/genericx86-64',
                 numPorts=70, **kwargs):
        kwargs['nodetype'] = "HalonSwitch"

        # During Halon CIT test run, CT/FT tests can be run on
        # multiple sandboxes at the same time.
        # Each sandbox needs a different docker switch image.
        # The top level makefile exports a ENV variable
        # with the docker image name for that test run.
        test_image = os.environ.get('VSI_IMAGE_NAME')
        if test_image is not None:
            image = test_image

        # Start Halon switch firmware in a docker
        super(HalonSwitch, self).__init__(name, image, **kwargs)

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

    def startCLI(self):
        # The vtysh shell is opened as subprocess in the docker
        # in interactive mode and the -t option in the vtysh adds
        # chr(127) in the prompt which we poll for in the read.
        cmd = ["docker","exec","-i",self.container_name, "/usr/bin/vtysh", "-t"]
        vtysh = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        self.cliStdin = vtysh.stdin
        self.cliStdout = vtysh.stdout

        # Wait for prompt
        data = self.readCLI(vtysh.stdout.fileno(), 1024)

    def startShell(self):

        DockerNode.startShell(self)

        # Wait until the OVSDB is up in the Halon switch.
        # Copy a script which waits until 'cur_hw' in the
        # Open_Vswitch tables becomes greater than 0
        dir, f = os.path.split(__file__)
        switch_wait = os.path.join(dir, "scripts", "wait_for_halonswitch")
        shutil.copy(switch_wait, self.shareddir)
        self.cmd("/shared/wait_for_halonswitch")

        self.startCLI()

    def writeCLI(self, fd, inp):
        os.write(fd, inp + "\n")

    def readCLI(self, fd, buflen=1024):
        out = ''
        while True:
            data = os.read(fd, buflen)
            if len(data) > 0:
                out += data
            if data[-1] == chr(127):
                out.replace(chr(127),'')
                break
        return out

    def cmdCLI(self, inp, waiting=True):
        if waiting:
            self.writeCLI(self.cliStdin.fileno(), inp)
            return self.readCLI(self.cliStdout.fileno(), 1024)
        else:
            self.writeCLI(self.cliStdin.fileno(), inp)
        return ''

    def stop(self, deleteIntfs=True):
        pass

    def swns_cmd(self, cmd):
        return self.cmd(SWNS_EXEC + cmd)

    # OVS commands add double quotes around the strings
    # in the output. This function removes them from the output.
    def ovscmd(self, cmd):
        out = self.cmd(cmd)

        # Remove all the double quotes in the output.
        out = out.replace('"', '')

        # Some of the OVS commands are printing multiple new lines.
        out = out.replace('\r\r','\r')

        return out

class HalonTest(object):
    def __init__(self, test_id=None, switchmounts=[], hostmounts=[], hostimage='ubuntu:latest', start_net=True):
        # If 'test_id' is not passed create a random UUID.
        # Docker is unable to handle a container name with complete UUID.
        # So take only the fifth field of it.
        if test_id is None:
            test_id = str(uuid.uuid4().fields[4])
            sbox_uuid = os.environ.get('SANDBOX_UUID')
            if sbox_uuid is not None:
                test_id = sbox_uuid + "-" + test_id

        self.id = test_id
        self.switchmounts = switchmounts
        self.hostmounts = hostmounts
        self.hostimage = hostimage

        # Set log level to 'debug' to enable Debugging.
        self.setLogLevel('info')
        info("\n============= HALON TEST START =============\n")

        self.testdir = "/tmp/halon-test/" + self.id
        shutil.rmtree(self.testdir, ignore_errors=True)
        os.makedirs(self.testdir)
        info("Test log dir: " + self.testdir + "\n")

        # Setup and start the network topology.
        if start_net is True:
            self.setupNet()
            self.net.start()

    def setLogLevel(self, levelname='info'):
        setLogLevel(levelname)

    def getNodeOpts(self):
        return {'testid': self.id, 'testdir': self.testdir}

    def setHostImageOpts(self, hostimage):
        self.hostimage = hostimage

    def getHostOpts(self):
        opts = self.getNodeOpts()
        opts.update({'mounts':self.hostmounts})
        opts.update({'HostImage':self.hostimage})
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
