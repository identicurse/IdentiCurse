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
        self.text = ""
        self.timed_update_restore_value = None

    def timed_update(self, text, delay=10):
        TimedUpdate(self, text, delay).start()

    def update(self, text):
        if self.timed_update_restore_value is None:
            self.text = text
            self.redraw()
        else:
            self.timed_update_restore_value = text

    def redraw(self):
        self.window.erase()
        maxx = self.window.getmaxyx()[1] - 2
        if len(self.text) >= (maxx):  # if the left text would end up too near the right text
            self.window.addstr(0, 1, self.text[:maxx-3].strip() + "...")
        else:
            self.window.addstr(0, 1, self.text)
        self.window.refresh()

class TimedUpdate(threading.Thread):
    def __init__(self, statusbar, text, delay):
        threading.Thread.__init__(self)

        self.statusbar = statusbar
        self.text = text
        self.delay = delay

    def run(self):
        self.statusbar.timed_update_restore_value = self.statusbar.text
        self.statusbar.update(self.text)

        time.sleep(self.delay)

        temp_restore_value = self.statusbar.timed_update_restore_value  # store this so we can reset the original, otherwise we hit the else clause in update
        self.statusbar.timed_update_restore_value = None
        self.statusbar.update(temp_restore_value)
