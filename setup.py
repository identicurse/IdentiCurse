#!/usr/bin/env python2
# Copyright (c) 2010, Identicurse developers
# All rights reserved.
"""
Standard build script.
"""

__docformat__ = 'restructuredtext'

import os.path

from setuptools import setup, find_packages

setup(
    name="identicurse",
    version='0.5-dev',
    description="A simple Identi.ca client with a curses-based UI.",
    long_description=("A simple Identi.ca client with a curses-based UI."),
    author="Psychedelic Squid and Reality",
    author_email='psquid@psquid.net and tinmachin3@gmail.com',
    url="http://identicurse.net/",
    download_url=("http://identicurse.net/release/"),

    license="GPLv3+",

    data_files=[('identicurse',['README', 'conf/config.json'])],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,

    entry_points={
        'console_scripts':
            ['identicurse = identicurse:main'],
    },

    classifiers=[
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
    ],
)
