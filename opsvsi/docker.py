#!/usr/bin/python

from mininet.net import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import *
from subprocess import *
import select
import os

# Using this constant for init_cmd will allow
# the docker image to execute # its own startup
# scripts/default CMD as defined in its corresponding Dockerfile.
DOCKER_DEFAULT_CMD = "DOCKER_DEFAULT_CMD"

# This function dumps the last "LINES_TO_DUMP" lines from the docker daemon logs
# Docker daemon logs can be gathered by different means depending on the host OS
# For example:
#    Ubuntu - /var/log/upstart/docker.log
#    CentOS - /var/log/daemon.log | grep docker
#    Boot2Docker - /var/log/docker.log
#    Debian GNU/Linux - /var/log/daemon.log
#    Fedora - journalctl -u docker.service
#    Red Hat Enterprise Linux Server - /var/log/messages | grep docker
#    OpenSuSE - journalctl -u docker.service
# For now we support the file based logs.

def dumpDockerLogFile():
    import os, platform

    LINES_TO_DUMP = 100
    DOCKER_LOG_FILE = ""
    DOCKER_FILTER = ""

    if os.path.isfile("/var/log/upstart/docker.log"):
        DOCKER_LOG_FILE = "/var/log/upstart/docker.log"
    elif os.path.isfile("/var/log/daemon.log"):
        DOCKER_LOG_FILE = "/var/log/daemon.log"
        DOCKER_FILTER = "docker"
    elif os.path.isfile("/var/log/messages"):
        DOCKER_LOG_FILE = "/var/log/messages"
        DOCKER_FILTER = "docker"
    else:
        error("dumpDockerLogFile: Unknown platform")
        return

    if os.path.isfile(DOCKER_LOG_FILE) and os.access(DOCKER_LOG_FILE, os.R_OK):
        with open(DOCKER_LOG_FILE, "r") as docker_log_file:
            if not DOCKER_FILTER:
                lines = docker_log_file.readlines()
            else:
                debug('dumpDockerLogFile: docker filter = %s' % DOCKER_FILTER)
                lines = [line for line in docker_log_file if DOCKER_FILTER in line]
    else:
        error("dumpDockerLogFile: Docker daemon log file not found")
        return

    #print last "LINES_TO_DUMP" lines
    debug("Printing last %d lines from the docker daemon log\n" % LINES_TO_DUMP)
    lines = lines[-LINES_TO_DUMP:]
    for line in lines:
        error(line)

class DockerNode(Node):
    def __init__(self, name, image='openswitch/ubuntutest', **kwargs):
        self.image = image

        self.testid = kwargs.pop('testid', None)
        self.container_name = self.testid + '-' + name

        self.testdir = kwargs.pop('testdir', None)
        self.nodedir = self.testdir + '/' + name
        os.makedirs(self.nodedir)

        self.shareddir = self.nodedir + '/shared'
        os.makedirs(self.shareddir)

        self.mounts = kwargs.pop('mounts', [])
        self.init_cmd = kwargs.pop('init_cmd', '/sbin/init')

        self.nodetype = kwargs.pop('nodetype', "VsiOpenSwitch")

        # Just in case test isn't running in a container,
        # clean up any mess left by previous run
        call(["docker rm -f " + self.container_name], stdout=PIPE,
             stderr=PIPE, shell=True)

        mountParams = []
        for mount in self.mounts:
            mountParams += ["-v", mount]

        # If OpsVsiHost simulate terminal, and run BASH
        if self.nodetype == "OpsVsiHost":
            dockerOptions = "-dt"
            self.init_cmd = "/bin/bash"
        else:
            dockerOptions = "-d"

        self.bashrc_file_name = "mininet_bash_rc"
        f = open(self.shareddir + '/' + self.bashrc_file_name, "w")
        f.write("export PS1='\177'")
        f.close()

        # /tmp File system on the docker app is wiped out
        # after starting the docker.
        # So don't create any files in /tmp directory of the docker app.
        env_cov_data_dir = os.environ.get('VSI_COV_DATA_DIR', None)
        if env_cov_data_dir is None:
            cmd = ["docker", "run", "--privileged",
                   "-v", self.shareddir + ":/shared",
                   "-v", "/dev/log:/dev/log",
                   "-v", "/lib/modules:/lib/modules",
                   "-v", "/sys/fs/cgroup:/sys/fs/cgroup"] + \
                   mountParams + \
                   ["-h", self.container_name, "--name=" + self.container_name,
                    dockerOptions, self.image]
        else:
            cmd = ["docker", "run", "--privileged",
                   "-v", self.shareddir + ":/shared",
                   "-v", "/dev/log:/dev/log",
                   "-v", "/sys/fs/cgroup:/sys/fs/cgroup",
                   "-v", "/lib/modules:/lib/modules",
                   "-v", env_cov_data_dir + ":" + env_cov_data_dir] +\
                   mountParams + \
                   ["-h", self.container_name, "--name=" + self.container_name,
                    dockerOptions, self.image]

        if self.init_cmd != DOCKER_DEFAULT_CMD:
            cmd.append(self.init_cmd)

        dPid = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        # do we have to read stdout/stderr now before we wait
        d_out = dPid.stdout.readlines();
        dPid.wait();
        if dPid.returncode != 0:
            # dump d_out and then abort I guess
            debug(d_out)
            error("Failed to start docker, cmd was: '%s'", cmd)
            dumpDockerLogFile()
            # Clean up any partial/zombie docker instance
            call(["docker rm -f "+self.container_name], stdout=PIPE,
                 stderr=PIPE, shell=True)
            raise Exception("Failed to start docker")

        # Wait until container actually starts and grab it's PID
        while True:
            pid_cmd = ["docker", "inspect", "--format='{{ .State.Pid }}'",
                       self.container_name]
            pidp = Popen(pid_cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                         close_fds=False)
            ps_out = pidp.stdout.readlines()
            pidp.wait()
            if pidp.returncode == 0:
                pid = int(ps_out[0])
                if pid != 0:
                    self.docker_pid = pid
                    debug("Docker container started.\n")
                    debug(" Name=" + self.container_name)
                    debug(" PID=", self.docker_pid)
                    break

        super(DockerNode, self).__init__(name, **kwargs)

    def popen(self, *args, **kwargs):
        return Node.popen(self, *args, mncmd=['docker', 'exec',
                          self.container_name],
                          **kwargs)

    def terminate(self):
        if self.shell:
            call(["docker rm -f "+self.container_name], stdout=PIPE,
                 stderr=PIPE, shell=True)
            self.cleanup()

    def startShell(self):
        if self.shell:
            error("%s: shell is already running")
            return

        cmd = ["mnexec", "-cd", "script", "-c",
               ' '.join(["docker", "exec", "-ti", self.container_name,
                         "/bin/bash", "--rcfile",
                         "/shared/" + self.bashrc_file_name]),
               "--timing=" + self.nodedir + "/transcript.timing",
               "-q", "-f", self.nodedir + "/transcript"]

        self.shell = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                           close_fds=True)
        self.stdin = self.shell.stdin
        self.stdout = self.shell.stdout
        self.pid = self.docker_pid
        self.pollOut = select.poll()
        self.pollOut.register(self.stdout)
        self.outToNode[self.stdout.fileno()] = self
        self.inToNode[self.stdin.fileno()] = self
        self.execed = False
        self.lastCmd = None
        self.lastPid = None
        self.readbuf = ''
        self.waiting = False

        # Wait for prompt
        while True:
            data = self.read(1024)
            if data[-1] == chr(127):
                break
            self.pollOut.poll()
        self.waiting = False
        # +m: disable job control notification
        self.cmd('unset HISTFILE; stty -echo; set +m')


class DockerHost (DockerNode):
    pass


class DockerLink(Link):
    def __init__(self, node1, node2, **kwargs):
        super(DockerLink, self).__init__(node1, node2, **kwargs)

    def makeIntfPair(cls, intfname1, intfname2, addr1=None, addr2=None,
                     node1=None, node2=None, deleteIntfs=True):

        node1_netns = " netns " + str(node1.pid) if node1.inNamespace else " "
        node1_netns_exec = "ip netns exec " + \
                           str(node1.pid) if node1.inNamespace else ""

        node2_netns = " netns " + str(node2.pid) if node2.inNamespace else " "
        node2_netns_exec = "ip netns exec " + \
                           str(node2.pid) if node2.inNamespace else ""

        if deleteIntfs:
            call([node1_netns_exec + " ip link del " + intfname1],
                 stdout=PIPE, shell=True)
            call([node2_netns_exec + " ip link del " + intfname2],
                 stdout=PIPE, shell=True)

        call(["ip link add " + node1_netns + " name " + intfname1 + " down " +
              " type veth peer " + node2_netns + " name " +
              intfname2 + " down "], shell=True)
