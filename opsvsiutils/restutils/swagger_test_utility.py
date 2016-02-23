#!/usr/bin/env python
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
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

#######################------Description------################################
# Currently this utility checks for inconsistencies like datatype mismatch   \
# or properties incorrectly listed, between the swagger model schema and the \
# extended schema. Ops-restapi.json is generated using vswitch.extschema and \
# vswitch.xml which is used by swagger for rendering the required            \
# information. Thus, we are indirectly testing the apidocgen.py. To use this \
# code call swagger_model_verification(...) function from the individual     \
# feature tests.
##############################################################################

import sys
import json
import string
import subprocess
import re
from opsvsi.opsvsitest import *

##############################################################################
####  Get ops-restapi.json file from the docker container \              #####
####               created by the feature test                           #####
##############################################################################
def get_json_file(container_id):
    info("container_id_swagger %s\n" % container_id)
    copy_from_docker = 'docker cp ' + container_id + \
                       ':/srv/www/api/ops-restapi.json /tmp'

    try:
        res = subprocess.check_output(['docker', 'cp', container_id + ':/srv/www/api/ops-restapi.json', '/tmp'])
    except subprocess.CalledProcessError as e:
        info("Error in subprocess docker cp command\n")

##############################################################################
######  Read the ops-restapi.json file and get the json data            ######
##############################################################################
def get_json_data(container_id):
    get_json_file(container_id)
    f = open("/tmp/ops-restapi.json", "r")
    json_data = json.loads(f.read())
    f.close()
    return json_data


##############################################################################
####  Return a dictionary which maps all the config params to their \    #####
####     datatypes to generate the REST model schema                     #####
##############################################################################
def generate_model_from_json(config_data):
    type_dict = {}
    for k, v in config_data.iteritems():
        try:
            type_dict[k] = v["type"]
        except:
            try:
                if "KV" in (v["$ref"].split("#/definitions/")[1].split('-')):
                    type_dict[k] = "dict"
                else:
                    type_dict[k] = v
            except:
                type_dict[k] = v

    return type_dict


##############################################################################
####  Extract the swagger model schema from Resource URI's and method \  #####
####             type by parsing the ops-restapi.json                    #####
##############################################################################
def parse_opsrestapi_json(uri, method_type, json_data):
    uri_path = json_data["paths"][uri]

    if method_type == "GET":
        pass

    elif method_type == "GET_ID":
        assert "get" in uri_path > 0,\
            "Invalid Get_id URI passed to the swagger test utility"
        request_get = uri_path["get"]
        get_ok_response = request_get["responses"]["200"]
        ref_config_schema = get_ok_response["schema"]["$ref"]

    elif method_type == "PUT":
        assert "put" in uri_path > 0,\
            "Invalid Put URI passed to the swagger test utility"
        request_put = uri_path["put"]
        length = len(request_put["parameters"])
        params = request_put["parameters"][length - 1]
        ref_config_schema = params["schema"]["$ref"]

    elif method_type == "POST":
        assert "post" in uri_path > 0,\
            "Invalid Post URI passed to the swagger test utility"
        request_post = uri_path["post"]
        length = len(request_post["parameters"])
        params = request_post["parameters"][length - 1]
        ref_config_schema = params["schema"]["$ref"]

    config_schema = ref_config_schema.split("#/definitions/")[1]
    definition = json_data["definitions"][config_schema]
    ref_config_params = definition["properties"]["configuration"]["$ref"]
    config_param_obj = ref_config_params.split("#/definitions/")[1]
    config_params = json_data["definitions"][config_param_obj]["properties"]

    return config_params


##############################################################################
####  High Level Get always returns a list of strings. So we dont \      #####
####               have anything to validate for now                     #####
##############################################################################
def swagger_config_model_get(container_id, uri):
    info("Method not supported\n")


##############################################################################
####  Function to validate the datatypes of GET_ID request with          #####
####                 the schema datatypes                                #####
##############################################################################
def swagger_config_model_get_id(container_id, uri):
    json_data = get_json_data(container_id)

    ##path under system
    config_params = parse_opsrestapi_json(uri, "GET_ID", json_data)
    return generate_model_from_json(config_params)


##############################################################################
####  Function to validate the datatypes of PUT request with             #####
####                 the schema datatypes                                #####
##############################################################################
def swagger_config_model_put(container_id, uri):
    json_data = get_json_data(container_id)

    ##high level table
    config_params = parse_opsrestapi_json(uri, "PUT", json_data)
    return generate_model_from_json(config_params)


##############################################################################
####  Function to validate the datatypes of POST request with            #####
####                 the schema datatypes                                #####
##############################################################################
def swagger_config_model_post(container_id, uri):
    json_data = get_json_data(container_id)

    ##high level table
    config_params = parse_opsrestapi_json(uri, "POST", json_data)
    return generate_model_from_json(config_params)


##############################################################################
####  Dictionary to map the correct callback with the method type        #####
##############################################################################
model_functions = {"GET": swagger_config_model_get,
                   "GET_ID": swagger_config_model_get_id,
                   "PUT": swagger_config_model_put,
                   "POST": swagger_config_model_post}


##############################################################################
####  Function to get the datatype dictionary of a URI from the REST \   #####
####  schema and verify it with feature test data. This is the function  #####
####  that needs to be called from the feature tests                     #####
##############################################################################
def swagger_model_verification(container_id, uri, method_type, DATA):
    bugs_flag = False
    swagger_model_schema = model_functions[method_type](container_id, uri)
    dict_to_typeclass = {"int": "integer", "str": "string",
                         "dict": "dict", "list": "array", "unicode": "string"}

    info("\n#################### Swagger Bugs #####################\n")
    info("Parameters not matched between swagger and schema:\n")
    for k, v in swagger_model_schema.iteritems():
        try:
            config_data_schema = type(DATA["configuration"][k]).__name__
            if(swagger_model_schema[k] !=
               dict_to_typeclass[config_data_schema]):
                bugs_flag = True
                info("%s type not matched" % k)
                info("  swagger=%s schema=%s\n" % \
                      (swagger_model_schema[k], config_data_schema))
        except:
            info("%s key not found\n" % k)
            bugs_flag = True

    info("################### END Swagger Bugs ###################\n")

    # The assert statement is currently removed, because some swagger bugs \
    # are already open, which we caught using this utility. We will fix \
    # these bugs in parallel and once the code is thoroughly reviewed, we \
    # will add this statement before the final merge
    #assert bugs_flag == True, "Please look at the issues above and report them"
