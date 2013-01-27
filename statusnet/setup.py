#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
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

from distutils.core import setup

setup(
    name = 'statusnet',
    py_modules = ['statusnet'],
    version = '0.1.1',
    install_requires=[
        "oauth >= 1.0.1",
        ],

    author = "Psychedelic Squid and Reality",
    author_email = '<psquid@psquid.net> and <tinmachin3@gmail.com>',
    url = 'http://identicurse.net/',

    description = 'A StatusNet library for Python.',
    long_description = """A StatusNet library for Python, used primarily by the
CLI client *IdentiCurse*.

This package is still in 0.x, expect breaking changes occasionally.""",

    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2 :: Only", # TODO: Get to the point this can be removed.
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ]
    )
