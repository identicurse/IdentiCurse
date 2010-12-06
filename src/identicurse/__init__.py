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

from identicurse import IdentiCurse
import random

SLOGANS = [
            "100% hippy-approved",
            "powered by hatred",
            "we don't get OAuth either",
            "don't drink and dent",
            "@psquid can't spell hippy",
            "Stupid sexy Flanders",
            "curry in the i-webs",
            "Got GNOME git commit access",
            "YOUR SOUL TO THE HOMOSEXUAL AGENDA",
            "Bullshit Bingo",
            "trying to do teh frees",
            "coming and coming and coming and coming",
            "Do you store your passwords in the back yard?",
            "Let's neuter this bullshit!",
            "it's probably just recycled bullshit.",
            "I'm on a rampage and kill everyone.",
            "a Tragedie in three parts.",
            "#metamicroblogging",
            "#metametamicroblogging",
            "EXCEPT IN NEBRASKA",
            "ATTENTION SNOW: GTFO ITS TOO WARM FOR YOU!",
            "eating paracetamol sandwiches."
          ]

def main():
    """
    Innit.
    """
    print "Welcome to IdentiCurse 0.4-dev - %s" % (random.choice(SLOGANS))
    IdentiCurse()


if __name__ == '__main__':
    main()
