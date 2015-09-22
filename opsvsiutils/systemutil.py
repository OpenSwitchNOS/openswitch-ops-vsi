# This file is used to add common functions
# that can be used across test scripts.

import re


def parsePing(pingOutput):
    '''Parse ping output and check to see if ping succeeded or failed'''
    # Check for downed link
    if 'Destination Host Unreachable' in pingOutput:
        return False
    r = r'(\d+) packets transmitted, (\d+) received'
    m = re.search(r, pingOutput)
    if m is None:
        return False
    sent, received = int(m.group(1)), int(m.group(2))
    if sent == received:
        return True
    else:
        return False
