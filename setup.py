#!/usr/bin/env python

"Setuptools params"

from setuptools import setup, find_packages
from os.path import join

# Get version number from source tree
import sys
sys.path.append( '.' )

VERSION = "0.0.1"

modname = distname = 'halonnet'

setup(
    name=distname,
    version=VERSION,
    description='Halon emulator based on Mininet',
    author='Michael Zayats',
    author_email='michael.zayats@hp.com',
    packages=[ 'halonnet' ],
    long_description="""
        Halonnet is an emulation platform to be used both during
        the development and testing of OpenHalon
        """,
    classifiers=[
          "License :: OSI Approved :: Apache Software License",
          "Programming Language :: Python",
          "Development Status :: 2 - Pre-Alpha",
          "Intended Audience :: Developers",
          "Topic :: System :: Emulators",
    ],
    keywords='networking emulator protocol Internet OpenFlow SDN',
    license='Apache Software License',
    install_requires=[
        'setuptools',
        'mininet'
    ],
    scripts=[],
)
