#!/usr/bin/python

from halonvsi.docker import *

OMD_DOCKER_IMAGE = 'openswitch/omd'

class OmdSwitch (DockerNode, Switch):
    def __init__(self, name, image=OMD_DOCKER_IMAGE, **kwargs):
        # Override init_cmd so that the Docker image can execute its own script.
        #kwargs['init_cmd'] = DOCKER_DEFAULT_CMD

        # Start OMD in a docker
        super(OmdSwitch, self).__init__(name, image, **kwargs)

        self.inNamespace = True

    def start(self, controllers):
        # Start Apache2 and OMD, if not already running
        pass
