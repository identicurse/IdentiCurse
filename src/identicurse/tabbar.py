# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Reality <tinmachin3@gmail.com> and Psychedelic Squid <psquid@psquid.net>
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

import curses

class TabBar(object):
    def __init__(self, window):
        self.window = window
        self.tabs = []
        self.current_tab = -1

    def update(self):
        self.window.erase()
        tab_string = ""
        for tab_num in xrange(len(self.tabs)):
            if tab_num == self.current_tab:
                prefix = " > "
                postfix = " < "
            else:
                prefix = "   "
                postfix = "   "
            tab_string = tab_string + prefix + self.tabs[tab_num] + postfix
        tab_string = tab_string.rstrip()  # removes the spare whitespace of the final prefix
        maxx = self.window.getmaxyx()[1]
        if len(tab_string) >= (maxx - 1):  # if the full tab list would be wider than the available display area
            self.window.addstr(0, 1, tab_string[:maxx-2])
        else:
            self.window.addstr(0, 1, tab_string)
        self.window.refresh()
