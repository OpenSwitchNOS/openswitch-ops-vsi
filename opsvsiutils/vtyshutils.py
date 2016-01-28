#!/usr/bin/python

# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from opsvsi.opsvsitest import *

VTYSH_CR = '\r\n'
ROUTE_MAX_WAIT_TIME = 300


class SwitchVtyshUtils(object):
    @staticmethod
    def vtysh_cmd(switch, cmd):
        if isinstance(switch, VsiOpenSwitch):
            return switch.cmdCLI(cmd)
        else:
            return switch.cmd("vtysh -c \"%s\"" % cmd)

    @staticmethod
    def vtysh_get_running_cfg(switch):
        return SwitchVtyshUtils.vtysh_cmd(switch, "sh running-config")

    @staticmethod
    def vtysh_print_running_cfg(switch):
        info(SwitchVtyshUtils.vtysh_get_running_cfg(switch))

    # Method for executing the configuration command in vtysh on an array of
    # configurations. Input must be an array of configurations, such as:
    #   ["router bgp 1", "bgp router-id 1.1.1.1"]
    @staticmethod
    def vtysh_cfg_cmd(switch, cfg_array, show_running_cfg=False,
                      show_results=False):
        if isinstance(switch, VsiOpenSwitch):
            SwitchVtyshUtils.vtysh_cfg_cmd_ops(switch, cfg_array, show_results)
        else:
            SwitchVtyshUtils.vtysh_cfg_cmd_quagga(switch, cfg_array,
                                                  show_results)

        if show_running_cfg:
            SwitchVtyshUtils.vtysh_print_running_cfg(switch)

    @staticmethod
    def vtysh_cfg_cmd_quagga(switch, cfg_array, show_results):
        exec_cmd = ' -c "configure term"'

        for cfg in cfg_array:
            exec_cmd += " -c \"%s\"" % cfg

        result = switch.cmd("vtysh %s" % exec_cmd)
        if show_results:
            info("### Config results: %s ###\n" % result)

    @staticmethod
    def vtysh_cfg_cmd_ops(switch, cfg_array, show_results):
        switch.cmdCLI('configure term')

        for cfg in cfg_array:
            result = switch.cmdCLI(cfg)
            if show_results:
                info("### Config results: %s ###\n" % result)

        switch.cmdCLI('end')

    # This method takes in an array of the config that we're verifying the
    # value for. For example, if we are trying to verify the remote-as of
    # neighbor:
    #    neighbor <router-id> remote-as <value>
    #
    # The input array should be ["neighbor", "remote-as"]. This will allow the
    # caller to avoid having to include the router-id. If the user wanted to
    # verify the remote-as value for a specific router-id, however, then the
    # user can construct the cfg_array as:
    #   ["neighbor", <router-id>, "remote-as"]
    @staticmethod
    def verify_cfg_value(switch, cfg_array, value):
        running_cfg = SwitchVtyshUtils.vtysh_get_running_cfg(switch)
        running_cfg = running_cfg.split(VTYSH_CR)

        for rc in running_cfg:

            for c in cfg_array:
                if (c in rc) and (str(value) in rc):
                    return True

        return False

    # Method for verifying if a configuration exists in the running-config.
    # The input is a configuration array. For example, if the user wants to
    # verify the configuration exists:
    #   neighbor <router-id> remote-as <value>
    #
    # The user can check if remote-as exists for a specific neighbor by passing
    # in a config array of:
    #   ["neighbor", <router-id>, "remote-as"]
    #
    # If the user doesn't want to check for a specific router-id, then the
    # following array can be passed-in:
    #   ["neighbor", "remote-as"]
    @staticmethod
    def verify_cfg_exist(switch, cfg_array):
        return SwitchVtyshUtils.verify_cfg_value(switch, cfg_array, '')

    # Method for waiting for a route for ROUTE_MAX_WAIT_TIME seconds.
    # The caller may define condition as True or False to look for
    # the existence or non-existence, correspondingly, of a route.
    # This function polls per second
    @staticmethod
    def wait_for_route(switch, network, next_hop, condition=True,
                       print_routes=False):
        for i in range(ROUTE_MAX_WAIT_TIME):
            attempt = i + 1
            found = SwitchVtyshUtils.verify_bgp_route(switch, network,
                                                      next_hop, attempt,
                                                      print_routes)

            if found == condition:
                if condition:
                    result = "Route was found"
                else:
                    result = "Route was not found"

                info("### %s ###\n" % result)
                return found

            sleep(1)

        info("### Condition not met after %s seconds ###\n" %
             ROUTE_MAX_WAIT_TIME)
        return found

    @staticmethod
    def verify_bgp_route(switch, network, next_hop, attempt=1,
                         print_routes=False):
        info("### Verifying route on switch %s [attempt #%d] - Network: %s, "
             "Next-Hop: %s ###\n" %
             (switch.name, attempt, network, next_hop))

        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp")

        if print_routes:
            info("### Routes for switch %s ###\n" % switch.name)
            info("%s\n" % routes)

        routes = routes.split(VTYSH_CR)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ipv6 bgp")

        if print_routes:
            info("### Routes for switch %s ###\n" % switch.name)
            info("%s\n" % routes)

        routes = routes.split(VTYSH_CR)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        return False

    @staticmethod
    def verify_show_ip_bgp_route(switch, network, next_hop):
        info("### Verifying - show ip bgp routei/show ipv6 bgp - Network: %s, "
             "Next-Hop: %s ###\n" % (network, next_hop))

        cmd = "sh ip bgp %s" % network
        routes = SwitchVtyshUtils.vtysh_cmd(switch, cmd).split(VTYSH_CR)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        cmd = "sh ipv6 bgp %s" % network
        routes = SwitchVtyshUtils.vtysh_cmd(switch, cmd).split(VTYSH_CR)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        return False
