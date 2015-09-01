#!/usr/bin/env python

"Setuptools params"

from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys
sys.path.append('.')

VERSION = "1.0.0"

distname = 'opsvsi'

setup(
    name=distname,
    version=VERSION,
    description='OpenSwitch test/development infrastructure based on Mininet',
    packages=[ 'halonvsi', 'opsvsi', 'halonutils', 'opsvsiutils' ],
    long_description="""
        OpenSwitchVSI is an emulation platform to be used both during
        the development and testing of OpenSwitch software.
        """,
    classifiers=[
          "License :: OSI Approved :: Apache Software License",
          "Programming Language :: Python",
          "Development Status :: 2 - Pre-Alpha",
          "Intended Audience :: Developers",
          "Topic :: System :: Emulators",
    ],
    license='Apache Software License',
    install_requires=[
        'setuptools',
        'mininet'
    ],
    package_data={'halonvsi' : ['scripts/*'], 'opsvsi' : ['scripts/*']},
    scripts=[],
)
