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

import os.path
try:
    import json
except ImportError:
    import simplejson as json

auth_fields = ["username", "password", "api_path", "consumer_key", "consumer_secret", "oauth_token", "oauth_token_secret", "use_oauth"]

class Config(dict):
    def __init__(self):
        pass
        
    def save(self, filename=None, auth_filename=None):
        if filename is None:
            filename = self.filename
        if auth_filename is None:
            auth_filename = self.auth_filename
        try:
            unclean_config = self.copy()
            clean_config = {}
            auth_config = {}
            for key, value in unclean_config.items():
                if key in auth_fields:
                    auth_config[key] = value
                elif key == "colours" and self.colourscheme_filename is not None:
                    open(self.colourscheme_filename, "w").write(json.dumps(value, indent=4))
                else:
                    clean_config[key] = value
            open(filename, "w").write(json.dumps(clean_config, indent=4))
            open(auth_filename, "w").write(json.dumps(auth_config, indent=4))
        except IOError:
            return False
        return True

    def load(self, filename=None, auth_filename=None):
        if filename is None:
            filename = self.filename
        if auth_filename is None:
            auth_filename = self.auth_filename
        try:
            self.clear()
            self.update(json.loads(open(filename, "r").read()))
            self.update(json.loads(open(auth_filename, "r").read()))
            if "colourscheme" in self:
                colours = None
                try:
                    self.colourscheme_filename = os.path.join(self.basedir, "colours", "%s.json" % (self['colourscheme']))
                    colourscheme = json.loads(open(self.colourscheme_filename, "r").read())
                    if not "colours" in colourscheme:
                        colourscheme["colours"] = {}
                    if not "custom_colours" in colourscheme:
                        colourscheme["custom_colours"] = {}
                    colours = {"colours":colourscheme["colours"], "custom_colours":colourscheme["custom_colours"]}
                except IOError:  # couldn't load colourscheme
                    print "Couldn't load your colourscheme (%s) successfully." % (self['colourscheme'])
                    self.colourscheme_filename = None
                if colours is not None:
                    self.update(colours)
        except IOError:
            return False
        return True

class SessionStore(object):
    def __init__(self):
        pass

config = Config()
session_store = SessionStore()
