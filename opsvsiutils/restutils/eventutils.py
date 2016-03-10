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

from opsvsi.opsvsitest import *
import json

# WebSocket message constants
WS_APPLICATION = 'application'
WS_DATA = 'data'
WS_TYPE = 'type'
WS_REQUEST = 'request'
WS_RESPONSE = 'response'
WS_STATUS = 'status'
WS_SUCCESS = 'successful'
WS_UNSUCCESS = 'unsuccessful'
WS_EVENT = 'event'

# Events message constants
STATUS = 'status'
SUCCESS = 'successful'
UNSUCCESS = 'unsuccessful'
TYPE = 'type'
EVENT_ID = 'event_id'
SUBSCRIPTIONS = 'subscriptions'
NOTIFICATIONS = 'notifications'
RESOURCE = 'resource'
TABLE = 'table'
ROW = 'row'
FIELDS = 'fields'
DETAILS = 'details'
MESSAGES = 'messages'
ERRORS = 'errors'
CHANGE = 'change'
UPDATED = 'updated'


def create_ws_event_request_json(data):
    '''
    Create an event subscription request with the following format:
    {
        "type": "request",
        "data": {
            ...
        }
    }
    '''
    event_request = {}
    event_request[WS_TYPE] = WS_REQUEST
    event_request[WS_APPLICATION] = WS_EVENT
    event_request[WS_DATA] = data

    info("### Request created with data: ###\n")
    info("%s\n\n" % event_request)

    return json.dumps(event_request)


def create_ws_event_subs_req_json(subscriptions_list):
    '''
    Create an event subscription request with the following format:
    {
        "type": "request",
        "data": {
            "event": {
                "subscriptions": [...]
            }
        }
    }
    '''
    event_data = create_subscription_request(subscriptions_list)
    return create_ws_event_request_json(event_data)


def create_subscription_request(subscriptions_list):
    sub_request = {}
    sub_request[SUBSCRIPTIONS] = subscriptions_list

    info("### Subscribing to event with the following request ###\n")
    info("%s\n\n" % sub_request)

    return sub_request


def validate_message_common(msg_dict, is_request):
    info("### Validating common message fields ###\n")

    type_expected = WS_REQUEST if is_request else WS_RESPONSE

    assert WS_TYPE in msg_dict, "'%s' missing" % WS_TYPE
    assert WS_APPLICATION in msg_dict, "'%s' missing" % WS_APPLICATION
    assert msg_dict[WS_TYPE] == type_expected, "Invalid message type"
    assert WS_DATA in msg_dict, "'%s' missing" % WS_DATA

    if not is_request:
        assert WS_STATUS in msg_dict, "'%s' missing" % WS_STATUS
        assert msg_dict[WS_STATUS] == WS_SUCCESS, "Unsuccessful msg"

    info("### Common message fields validated. ###\n")


def validate_ws_event_message(msg_json, is_request, validate_success=True):
    msg_dict = json.loads(msg_json)
    validate_message_common(msg_dict, is_request)

    return validate_event_message(msg_dict[WS_DATA],
                                  is_request, validate_success)


def validate_event_message(event_data_dict, is_request, validate_success=True):
    info("### Validating event message ###\n")
    info("%s\n\n" % event_data_dict)

    if not is_request:
        assert STATUS in event_data_dict, "'%s' missing" % STATUS

        status_to_validate = UNSUCCESS
        if validate_success:
            status_to_validate = SUCCESS
        else:
            assert ERRORS in event_data_dict, "'%s' missing" % ERRORS

            # Validate fields for each error
            errors = event_data_dict[ERRORS]
            for error in errors:
                assert EVENT_ID in error, "'%s' missing" % EVENT_ID
                assert MESSAGES in error, "'%s' missing" % MESSAGES

        # Verify the status since it is a response
        received_status = event_data_dict[STATUS]
        assert received_status == status_to_validate, \
            "Unexpected status '%s'" % received_status

    info("### Event message validated. ###\n")
    return event_data_dict


def validate_event_notification(notif_req_json):
    info("### Notification from server received ###\n")
    info("### Validating notification request from server ###\n")
    is_request = True
    notif_req = validate_ws_event_message(notif_req_json, is_request)

    assert NOTIFICATIONS in notif_req, "Invalid event request"

    notifications = notif_req[NOTIFICATIONS]
    for notification in notifications:
        assert EVENT_ID in notification, "'%s' missing" % EVENT_ID
        assert CHANGE in notification, "'%s' missing" % CHANGE

    info("### Notification request validated. ###\n")
    return notifications


def verify_notifications_recv(subscriptions, notifications,
                              change_type=UPDATED):
    info("### Verifying notifications received ###\n")

    for subscription in subscriptions:
        event_id = subscription[EVENT_ID]

        # Ensure notification received for subscribed events
        matched_notif = None
        for notification in notifications:
            if event_id == notification[EVENT_ID]:
                matched_notif = notification
                break

        assert matched_notif, "No notification for event %s" % event_id

        # Verify specific fields for row event subscriptions.
        resource_type = subscription[TYPE]
        if resource_type == ROW:
            info("### Verifying fields for row event notifications ###\n")

            # Regardless of subscribed to specific fields or not,
            # the details field should exist.
            assert DETAILS in matched_notif, "'%s' missing" % DETAILS

            # If subscribed to specific fields, ensure notification
            # includes the fields in the details.
            fields = subscription[FIELDS]
            for field in fields:
                assert field in matched_notif[DETAILS], \
                    "'%s' missing from notification" % field

        # Verify the change type received
        recv_change_type = matched_notif[CHANGE]
        assert change_type == recv_change_type, \
            "Unexpected change type '%s'" % recv_change_type

    info("### Verified notifications against subscriptions ###\n")


def verify_subscription_error(event_id, error_str, sub_response):
    info("### Verifying error received for: %s ###\n" % error_str)
    errors = sub_response[ERRORS]
    assert len(errors) == 1, "Unexpected number of errors"

    # Verify error received matches.
    error = errors[0]
    assert error[EVENT_ID] == event_id, \
        "Event id for error does not match subscription"

    error_messages = error[MESSAGES]
    assert len(error_messages) == 1, "Unexpected number of error messages"

    error_message = error_messages[0]
    assert error_str in error_message, "Unexpected error message."


def set_subscribed_fields(subscription, fields):
    subscription[FIELDS] = fields


def get_subscription_resource(subscription):
    return subscription[RESOURCE]


def set_subscription_resource(subscription, resource):
    subscription[RESOURCE] = resource


def get_event_id(subscription):
    return subscription[EVENT_ID]
