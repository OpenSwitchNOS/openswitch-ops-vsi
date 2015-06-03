#!/usr/bin/python

from mininet.net import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import *
from subprocess import *
import select


class DockerNode(Node):
    def __init__(self, name, image='ubuntu', **kwargs):
        self.image = image

        self.testid = kwargs.pop('testid', None)
        self.container_name = self.testid + '_' + name

        self.testdir = kwargs.pop('testdir', None)
        self.nodedir = self.testdir + '/' + name
        os.makedirs(self.nodedir)

        self.shareddir = self.nodedir + '/shared'
        os.makedirs(self.shareddir)

        self.mounts = kwargs.pop('mounts', [])

        # Just in case test isn't running in a container,
        # clean up any mess left by previous run
        call( [ "docker rm -f " + self.container_name ], stdout=PIPE,
                stderr=PIPE, shell=True)

        mountParams = []
        for mount in self.mounts:
            mountParams += ["-v", mount]

        self.bashrc_file_name = "mininet_bash_rc"
        f = open(self.shareddir + '/' + self.bashrc_file_name, "w")
        f.write("export PS1='\177'")
        f.close()

        # /tmp File system on the docker app is wiped out after starting the docker.
        # So don't create any files in /tmp directory of the docker app.
        cmd = ["docker", "run", "--privileged",
              "-v", self.shareddir + ":/shared",
              "-v", "/dev/log:/dev/log"] + \
              mountParams + \
              ["-h", self.container_name, "--name=" + self.container_name,
               "-d", self.image, "/sbin/init"]

        Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

        # Wait until container actually starts and grab it's PID
        while True:
            pid_cmd = [ "docker", "inspect", "--format='{{ .State.Pid }}'",
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
                    debug(" Name=" + self.container_name);
                    debug(" PID=", self.docker_pid);
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

        cmd = [ "mnexec", "-cd", "script", "-c",
                    ' '.join( [ "docker", "exec", "-ti", self.container_name,
                                "/bin/bash", "--rcfile", "/shared/" + self.bashrc_file_name]),
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
