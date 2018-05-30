#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Five in a row',
    'author': 'Mitnyik Levente',
    'url': 'https://github.com/mitle/fiveinarow',
    'download_url': 'https://github.com/mitle/fiveinarow',
    'author_email': 'mitnyik.levente@hallgato.ppke.hu',
    'version': '0.1',
    'install_requires': ['pygame', 'zmq', 'numpy', 'rsa', 'cryptography', 'nose'],
    'packages': ['fiveinarow'],
    'scripts': [],
    'name': 'fiveinarow'
}

setup(**config)
