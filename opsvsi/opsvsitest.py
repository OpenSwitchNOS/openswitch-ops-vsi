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
import shutil
import select
import re
import argparse
import os
import uuid
import pytest

SWNS_EXEC = '/sbin/ip netns exec swns '


class OpsVsiHost (DockerHost):
    def __init__(self, name, **kwargs):
        kwargs['nodetype'] = "OpsVsiHost"

        image = kwargs.pop('HostImage')
        super(OpsVsiHost, self).__init__(name, image, **kwargs)


class OpsVsiLink(DockerLink):
    def intfName(self, node, n):
        if isinstance(node, VsiOpenSwitch):
            return repr(n)
        else:
            return super(OpsVsiLink, self).intfName(node, n)


class VsiOpenSwitch (DockerNode, Switch):
    def __init__(self, name, image='openswitch/genericx86-64',
                 numPorts=54, **kwargs):
        kwargs['nodetype'] = "VsiOpenSwitch"

        # During OpenSwitch CIT test run, CT/FT tests
        # can be run on multiple sandboxes at the same time.
        # Each sandbox needs a different docker switch image.
        # The top level makefile exports a ENV variable
        # with the docker image name for that test run.
        test_image = os.environ.get('VSI_IMAGE_NAME')
        if test_image is not None:
            image = test_image

        # Start Openswitch firmware in a docker
        super(VsiOpenSwitch, self).__init__(name, image, **kwargs)

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

        # In generic-X86 image ports 49-54 are QSFP splittable ports.
        # so create subports for them.
        for i in irange(49, 54):
            for j in irange(1, 4):
                self.cmd(SWNS_EXEC + "/sbin/ip tuntap add dev " + str(i) + "-" + str(j) + " mode tap")

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
        cmd = ["docker", "exec", "-i", self.container_name, "/usr/bin/vtysh", "-t", "-vCONSOLE:ERR"]
        vtysh = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
        self.cliStdin = vtysh.stdin
        self.cliStdout = vtysh.stdout

        # Wait for prompt
        data = self.readCLI(vtysh.stdout.fileno(), 1024)

    def startShell(self):

        DockerNode.startShell(self)

        # Wait until the OVSDB is up in the Openswitch.
        # Copy a script which waits until 'cur_hw' in the
        # System tables becomes greater than 0
        dir, f = os.path.split(__file__)
        switch_wait = os.path.join(dir, "scripts", "wait_for_openswitch")
        shutil.copy(switch_wait, self.shareddir)
        self.cmd("/shared/wait_for_openswitch")
        script_output = self.cmd("cat /shared/logs")
        script_status = script_output.splitlines()[0]

        if 'Failure' in script_status:
            logs = "Container Name: " + self.container_name

            cmd1 = ['docker', 'ps', '-a']
            docker_ps = Popen(cmd1, stdout=PIPE)
            out = docker_ps.communicate()[0]
            logs = logs + "\nDocker ps :\n" + str(out)

            cmd2 = ['docker', 'logs', self.container_name]
            docker_logs = Popen(cmd2, stdout=PIPE)
            out = docker_logs.communicate()[0]
            logs = logs + "Docker logs :\n" + str(out)

            cmd3 = ['cat', '/var/log/syslog']
            cmd4 = ['grep' , 'switchd']
            cat_cmd = Popen(cmd3, stdout=PIPE)
            grep_cmd = Popen(cmd4, stdin=cat_cmd.stdout, stdout=PIPE)
            out = grep_cmd.communicate()[0]
            logs = logs + "Switchd logs :\n" + str(out)

            switch_logs = os.path.join(self.shareddir, "logs")
            f = open(switch_logs, 'a')
            f.write(logs)
            f.close()

#            ls_coredump = self.cmd("ls /var/lib/systemd/coredump/")
#            logs = logs + "ls_coredump :\n" + ls_coredump
            self.cmd("cp -rf /var/lib/systemd/coredump /shared/coredump")

            self.switchd_failed = True

        else:
            self.switchd_failed = False

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
                out.replace(chr(127), '')
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
        out = out.replace('\r\r', '\r')

        return out


class OpsVsiTest(object):
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
        info("\n============= OpenSwitchVsi TEST START =============\n")

        self.testdir = "/tmp/openswitch-test/" + self.id
        shutil.rmtree(self.testdir, ignore_errors=True)
        os.makedirs(self.testdir)
        info("Test log dir: " + self.testdir + "\n")

        # Setup and start the network topology.
        if start_net is True:
            self.setupNet()
            for switch in self.net.switches:
                if switch.switchd_failed:
                    self.net.stop()
                    pytest.exit("Switchd failed to start up")
            self.net.start()

    def setLogLevel(self, levelname='info'):
        setLogLevel(levelname)

    def getNodeOpts(self):
        return {'testid': self.id, 'testdir': self.testdir}

    def setHostImageOpts(self, hostimage):
        self.hostimage = hostimage

    def getHostOpts(self):
        opts = self.getNodeOpts()
        opts.update({'mounts': self.hostmounts})
        opts.update({'HostImage': self.hostimage})
        return opts

    def getSwitchOpts(self):
        opts = self.getNodeOpts()
        opts.update({'mounts': self.switchmounts})
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
                           switch=VsiOpenSwitch,
                           host=OpsVsiHost,
                           link=OpsVsiLink,
                           controller=None,
                           build=True)
