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

import json

class Config(dict):
    def __init__(self):
        pass
        
    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        try:
            open(filename, "w").write(json.dumps(self.copy(), indent=4))
        except IOError:
            return False
        return True

    def load(self, filename=None):
        if filename is None:
            filename = self.filename
        try:
            self.clear()
            self.update(json.loads(open(filename, "r").read()))
        except IOError:
            return False
        return True

class SessionStore(object):
    def __init__(self):
        pass

config = Config()
session_store = SessionStore()
