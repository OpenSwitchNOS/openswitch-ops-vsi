#!/usr/bin/python

from halonvsi.docker import *

OMD_DOCKER_IMAGE = 'openswitch/omd'

class OmdSwitch (DockerNode, Switch):
    def __init__(self, name, image=OMD_DOCKER_IMAGE, **kwargs):
        # Start OMD in a docker
        super(OmdSwitch, self).__init__(name, image, **kwargs)

        self.inNamespace = True

    def start(self, controllers):
        pass
