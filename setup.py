#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup

root = os.path.abspath(os.path.dirname(__file__))

version = __import__('pkit').__version__

setup(
    name='process-kit',
    version=version,
    license='MIT',

    author='Oleiade',
    author_email='tcrevon@gmail.com',
    url='http://github.com/botify-labs/pkit',
    keywords='',

    packages=[
        'pkit',

        'pkit.slot'
    ],
)
