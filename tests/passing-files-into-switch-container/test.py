#!/usr/bin/python

from sys import *
from subprocess import *

if __name__ == '__main__':
    exit(call(['./test-under-test.py --sm `pwd`/printme.sh:/printme.sh \
                --hm `pwd`/printme.sh:/printme.sh'], shell=True))
