#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Standard build script.
"""

__docformat__ = 'restructuredtext'

import os.path

from setuptools import setup, find_packages

setup(
    name="identicurse",
    version='0.4',
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
