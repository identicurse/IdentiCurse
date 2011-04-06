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
        self.left_index = 0

    def update(self):
        tab_list = []
        maxx = self.window.getmaxyx()[1] - 2
        total_length = 0
        for tab_num in xrange(len(self.tabs)):
            if tab_num == 0:
                tab_list.append((" ", identicurse.colour_fields['tabbar']))
                total_length += 1
            else:
                tab_list.append((" "*2, identicurse.colour_fields['tabbar']))
                total_length += 2
            if tab_num == self.current_tab:
                if (total_length + len(self.tabs[tab_num])) > (maxx + self.left_index):  # if this tab would end beyond the right-hand edge
                    self.left_index = (total_length + len(self.tabs[tab_num])) - (maxx - 1)
                elif total_length < self.left_index:  # if this tab would begin beyond the left-hand edge
                    self.left_index = total_length - 1
                attr = identicurse.colour_fields['tabbar_active']
            else:
                attr = identicurse.colour_fields['tabbar']
            if (not config.config["enable_colours"]) and (tab_num == self.current_tab):
                tab_list.append((self.tabs[tab_num].upper(), attr))
            else:
                tab_list.append((self.tabs[tab_num], attr))
            total_length += len(self.tabs[tab_num])
        self.window.erase()
        char_index = 0
        for block in tab_list:
            for char in block[0]:
                if char_index < self.left_index:
                    pass
                elif char_index > (maxx + self.left_index):
                    pass
                else:
                    self.window.addstr(char, curses.color_pair(block[1]))
                char_index += 1
        self.window.refresh()
