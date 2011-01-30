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

import curses, identicurse, config

class TabBar(object):
    def __init__(self, window):
        self.window = window
        self.tabs = []
        self.current_tab = -1

    def update(self):
        self.window.erase()
        tab_list = []
        total_length = 0
        for tab_num in xrange(len(self.tabs)):
            tab_list.append((" "*2, identicurse.colour_fields['tabbar']))
            if tab_num == self.current_tab:
                attr = identicurse.colour_fields['tabbar_active']
            else:
                attr = identicurse.colour_fields['tabbar']
            if (not config.config["enable_colours"]) and (tab_num == self.current_tab):
                tab_list.append((self.tabs[tab_num].upper(), attr))
            else:
                tab_list.append((self.tabs[tab_num], attr))
            total_length += (1 + len(self.tabs[tab_num]))
        maxx = self.window.getmaxyx()[1]
        if total_length >= (maxx - 1):  # if the full tab list would be wider than the available display area
            # TODO: handle this
            pass
        else:
            remaining_line_length = maxx - 2
            for block in tab_list:
                self.window.addstr(block[0], curses.color_pair(block[1]))
                remaining_line_length -= len(block[0])
            if remaining_line_length > 0:
                self.window.addstr(" "*remaining_line_length, curses.color_pair(identicurse.colour_fields['tabbar']))
        self.window.refresh()
