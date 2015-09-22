#!/usr/bin/python

from docker import *

QUAGGA_DOCKER_IMAGE = 'openswitch/quagga'

# This is the default router bgp ASN. This is used for clearing
# the BGP configurations so that bgp test scripts can apply
# configurations. By default, the Quagga docker image already configures
# router bgp 7675.
QUAGGA_DOCKER_DEFAULT_BGP_ASN = "7675"


class QuaggaSwitch (DockerNode, Switch):
    def __init__(self, name, image=QUAGGA_DOCKER_IMAGE, **kwargs):
        # Override init_cmd so that the Docker image can execute its own script.
        kwargs['init_cmd'] = DOCKER_DEFAULT_CMD

        # Start Quagga switch in a docker
        super(QuaggaSwitch, self).__init__(name, image, **kwargs)

        self.inNamespace = True

    def start(self, controllers):
        # Wait until bgpd and zebra daemons are started
        while True:
            bgp_pid = self.cmd("pgrep -f bgpd").strip()

            if bgp_pid != "":
                # Now that bgpd is running, remove the default bgp config
                cmd = '-c "configure term" '
                cmd += "-c \"no router bgp %s\"" % QUAGGA_DOCKER_DEFAULT_BGP_ASN

                self.cmd("vtysh %s" % cmd)
                break
