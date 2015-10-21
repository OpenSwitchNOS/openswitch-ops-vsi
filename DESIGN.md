# High level design of ops-vsi
ops-vsi is *OpenSwitch* Development/Test infrastructure based on *Mininet*.

## Overview
*Mininet* is a network emulator. It runs a collection of end-hosts, switches, and links on a single Linux kernel. It uses lightweight virtualization to make a single system look like a complete network, running the same kernel, system, and user code. ops-vsi is an extension to *Mininet*. In ops-vsi a switches are light weight docker container running *OpenSwitch* firmware. A special build of *OpenSwitch* firmware can run in a docker container. Multiple such dockers can be run in a single Linux machine and act as independent switches. In ops-vsi a end-host can be a docker container or a BASH running it a network namespace. *Mininet* can emulate virtual links between these switches & Hosts. A test developer can use these concepts and create a custom topology of switch & end-hosts connected to each other.

## Design

### Mininet extension
In *Mininet* a *node* can be a switch or end-host or router. Each node is created in its own network namespace. Linux Virtual Ethernet device pairs (veth) simulates links between these nodes. In regular *Mininet* a switch is simulated using OpenVswitch running in the Linux host default name space. End-hosts are simple BASH processes runnings in their own name space. In Ops-VSI a Switch is a shell executed in a Docker container running the complete OpenSwitch Image. In ops-vsi a end-host can be a shell executed in a Docker Container (running any image from Docker Hub or a locally built image) or can be a simple BASH.

In ops-vsi a developer can create any kind of custom topology. It can have any number of switches and end-hosts. They can have any number of links between them. Link speeds can be configured to any value that the host Linux kernel allows.
```
  Docker1               Docker2
 +------------------+   +------------------+   Docker3
 |                  |   |                  |   +-----------------+
 |                  |   |                  |   |Quagga Switch/   |
 |  OpenSwitch 1    |   | OpenSwitch 2     |   |Radius Switch/   |
 |                  |   |                  |   |Ubuntu/          |       +-------------+
 |                  |   |                  |   |Custom Docker    |       |     Bash    |
++-----+-----+---+--+---+--+--+------+-----+----------+----------+-------+------^------+------+
|      |     |   |         |  |      |                ^                         |             |
|      |     |   +---------+  |      |                |                         |             |
|      |     +----------------+      |                |                         |             |
|      +----------------------------------------------+                         |             |
|                                    +------------------------------------------+             |
|                                                                                             |
|                               Linux Kernel                                                  |
|                                                                                             |
+---------------------------------------------------------------------------------------------+
```

### Docker usage in ops-vsi
In common practise, a single application is run in a given container. Running multiple processes is rare practice. In ops-vsi we run the entire *OpenSwitch* firmware in a single docker.
OpenSwitch docker is created with the following command.
```
docker run --privileged -v <shareddir>:/shared -v /dev/log:/dev/log -v /sys/fs/cgroup:/sys/fs/cgroup  -h <container_name> --name= <container_name> -d <image> /sbin/init
docker exec -ti <container_name> bash
```
*OpenSwitch* distribution uses systemd as 'init' process. systemd will spawn all the daemons inside the docker. To run systemd inside a docker, it should be in *privileged* mode, and it should also mount /sysd/fs/cgroup filesystem.
A local directory from the host Linux machine is mounted as "/shared" to share files between Linux host machine and the docker container.

While creating a *end-host* node, a docker container with simple Bash is run as the only application inside the container. In ops-vsi there is flexibility to run any docker image with any kind of applications/tools in it. Custom images built & saved in docker hub can be used in the tests.

### How to write test using ops-vsi
The following is example code where you can run a simple ping test between a switch interface with routing enabled, and a host attached to it.
```python
class SwitchTest(OpsVsiTest):

  def setupNet(self):
    # if you override this function, make sure to
    # either pass getNodeOpts() into hopts/sopts of the topology that
    # you build or into addHost/addSwitch calls
    self.net = Mininet(topo=CustomTopology(hsts=2, sws=1,
                                           hopts=self.getHostOpts(),
                                           sopts=self.getSwitchOpts()),
                                           switch=VsiOpenSwitch,
                                           host=OpsVsiHost,
                                           link=OpsVsiLink, controller=None,
                                           build=True)
    def test1(self):
        s1 = self.net.switches[0]
        h1 = self.net.hosts[0]

        # Configure the switch for L3 routing.
        s1.cmdCLI("configure terminal")
        s1.cmdCLI("interface 1")
        s1.cmdCLI("ip address 10.12.12.12/8")

        ret = h1.cmd("ping -c 1 10.12.12.12")

        # Check if the ping return status.

        # END OF TEST

def main():
        test_class = SwitchTest()
        test_class.test1()


if __name__ == "__main__":
    main()
```
## References
* [Mininet](http://mininet.org)
* [Docker](https://www.docker.com)
