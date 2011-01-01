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

import threading, time, curses

class StatusBar(object):
    def __init__(self, window):
        self.window = window
        self.left_text = ""
        self.right_text = ""

    def update_left(self, text):
        self.left_text = text
        self.update()
    
    def update_right(self, text):
        self.right_text = text
        self.update()

    def timed_update_left(self, text, delay=10):
        TimedUpdate(self, 'left', text, delay).start()

    def timed_update_right(self, text, delay=10):
        TimedUpdate(self, 'right', text, delay).start()

    def update(self):
        self.window.erase()
        right_x = self.window.getmaxyx()[1] - (len(self.right_text) + 2)
        if len(self.left_text) >= (right_x - 3):  # if the left text would end up too near the right text
            self.window.addstr(0, 1, self.left_text[:right_x-6].strip() + "...")
        else:
            self.window.addstr(0, 1, self.left_text)
        self.window.addstr(0, right_x, self.right_text)
        self.window.refresh()

class TimedUpdate(threading.Thread):
    def __init__(self, statusbar, side, text, delay):
        threading.Thread.__init__(self)

        self.statusbar = statusbar
        self.side = side
        self.text = text
        self.delay = delay

    def run(self):
        initial_value = getattr(self.statusbar, self.side + "_text")

        update_function = getattr(self.statusbar, "update_" + self.side)
        update_function(self.text)

        time.sleep(self.delay)

        update_function(initial_value)
