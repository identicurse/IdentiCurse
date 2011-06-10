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

import os, sys, curses, locale, re, subprocess, random, platform
try:
    import json
except ImportError:
    import simplejson as json
from threading import Timer
from textbox import Textbox
import urllib2

from statusnet import StatusNet, StatusNetError
from tabbage import *
from statusbar import StatusBar
from tabbar import TabBar

import config
import helpers

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

colour_fields = {
    "none": 0,
    "statusbar": 1,
    "timelines": 2,
    "selector": 4,
    "username": 5,
    "time": 6,
    "source": 7,
    "notice_count": 8,
    "notice": 9,
    "profile_title": 10,
    "profile_fields": 11,
    "profile_values": 12,
    "group": 13,
    "tag": 14,
    "search_highlight": 15,
    "tabbar": 16,
    "tabbar_active": 17,
    "notice_link": 18,
    "warning": 19,
    "pause_line": 20,
}

if platform.system() == "Windows":  # Handle Windows' colour-order fuckery. This is only true if we are running on pure Windows. If we're on Cygwin, which handles colours correctly anyway, this won't match.
    colours = {
        "none": -1,
        "black": 0,
        "blue": 1,
        "green": 2,
        "cyan": 3,
        "red": 4,
        "magenta": 5,
        "brown": 6,
        "white": 7,
        "grey": 8,
        "light_blue": 9,
        "light_green": 10,
        "light_cyan": 11,
        "light_red": 12,
        "light_magenta": 13,
        "yellow": 14,
        "light_white": 15
    }
else:
    colours = {
        "none": -1,
        "black": 0,
        "red": 1,
        "green": 2,
        "brown": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "white": 7,
        "grey": 8,
        "light_red": 9,
        "light_green": 10,
        "yellow": 11,
        "light_blue": 12,
        "light_magenta": 13,
        "light_cyan": 14,
        "light_white": 15
    }

base_colours = {}

domain_regex = re.compile("http(s|)://(www\.|)(.+?)/.*")

oauth_consumer_keys = {
    "identi.ca": "d4f54e34af11ff8d35b79b7557ad771c",
    }
oauth_consumer_secrets = {
    "identi.ca": "8fb75c0a9bbca78fe0e85acc62a9169c",
    }

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self, additional_config={}):
        helpers.set_terminal_title("IdentiCurse")
        if hasattr(sys, "frozen"):  # if this matches, we're running under py2exe, so we need to do some magic to get the correct path
            executable_path = sys.executable
        else:
            executable_path = __file__
        self.path = os.path.dirname(os.path.realpath(unicode(executable_path, sys.getfilesystemencoding())))
        self.qreply = False
        
        if "config_dirname" in additional_config:
            config.config.basedir = os.path.expanduser(additional_config['config_dirname'])
        else:
            config.config.basedir = os.path.join(os.path.expanduser("~") ,".identicurse")
        config.config.filename = os.path.join(config.config.basedir, "config.json")
        config.config.auth_filename = os.path.join(config.config.basedir, "auth.json")

        if os.path.exists(config.config.basedir) and not os.path.isdir(config.config.basedir):  # (if a .identicurse file, as used by <= 0.7.x, exists)
            config_temp = open(config.config.basedir, "r").read()
            os.remove(config.config.basedir)
            os.mkdir(config.config.basedir)
            open(config.config.filename, "w").write(config_temp)

        if not os.path.exists(config.config.basedir):
            os.mkdir(config.config.basedir)

        if os.path.exists(config.config.filename) and not os.path.exists(config.config.auth_filename):
            unclean_config = json.loads(open(config.config.filename, "r").read())
            clean_config = {}
            auth_config = {}
            for key, value in unclean_config.items():
                if key in config.auth_fields:
                    auth_config[key] = value
                else:
                    clean_config[key] = value
            open(config.config.filename, "w").write(json.dumps(clean_config, indent=4))
            open(config.config.auth_filename, "w").write(json.dumps(auth_config, indent=4))

        try:
            if os.path.exists(config.config.filename) or os.path.exists(os.path.join("/etc", "identicurse.conf")):
                if not config.config.load():
                    config.config.load(os.path.join("/etc", "identicurse.conf"))
            else:
                import getpass, time
                # no config yet, so let's build one
                print os.path.join(self.path, "config.json")
                config.config.load(os.path.join(self.path, "config.json"))
                print "No config was found, so we will now run through a few quick questions to set up a basic config for you (which will be saved as %s so you can manually edit it later). If the default (where defaults are available, they're stated in []) is already fine for any question, just press Enter without typing anything, and the default will be used." % (config.config.filename)
                print "This version of IdentiCurse supports OAuth login. Using OAuth to log in means that you do not need to enter your username and password."
                use_oauth = raw_input("Use OAuth [Y/n]? ").upper()
                if use_oauth == "":
                    use_oauth = "Y"
                if use_oauth[0] == "Y":
                    config.config['use_oauth'] = True
                else:
                    config.config['use_oauth'] = False
                if not config.config['use_oauth']:
                    config.config['username'] = raw_input("Username: ")
                    config.config['password'] = getpass.getpass("Password: ")
                api_path = raw_input("API path [%s]: " % (config.config['api_path']))
                if api_path != "":
                    if api_path[:7] != "http://" and api_path[:8] != "https://":
                        api_path = "http://" + api_path
                    if api_path[:5] != "https":
                        https_api_path = "https" + api_path[4:]
                        response = raw_input("You have not used an https URL. This means everything you do with IdentiCurse will travel over your connection _unencrypted_. Would you rather use '%s' as your API path [Y/n]? " % (https_api_path)).upper()
                        if response == "":
                            response = "Y"
                        if response[0] == "Y":
                            api_path = https_api_path
                    config.config['api_path'] = api_path
                update_interval = raw_input("Auto-refresh interval (in whole seconds) [%d]: " % (config.config['update_interval']))
                if update_interval != "":
                    try:
                        config.config['update_interval'] = int(update_interval)
                    except ValueError:
                        print "Sorry, you entered an invalid interval. The default of %d will be used instead." % (config.config['update_interval'])
                notice_limit = raw_input("Number of notices to fetch per timeline page [%d]: " % (config.config['notice_limit']))
                if notice_limit != "":
                    try:
                        config.config['notice_limit'] = int(notice_limit)
                    except ValueError:
                        print "Sorry, you entered an invalid number of notices. The default of %d will be used instead." % (config.config['notice_limit'])
                try:
                    if config.config['use_oauth']:
                        instance = domain_regex.findall(config.config['api_path'])[0][2]
                        if not instance in oauth_consumer_keys:
                            print "No suitable consumer keys stored locally, fetching latest list..."
                            req = urllib2.Request("http://identicurse.net/api_keys.json")
                            resp = urllib2.urlopen(req)
                            api_keys = json.loads(resp.read())
                            if not instance in api_keys['keys']:
                                sys.exit("Sorry, IdentiCurse currently lacks the API keys needed to support OAuth with your instance (%(instance)s). If %(instance)s is a public instance, let us know which one it is, and we'll add support as soon as possible." % (locals()))
                            else:
                                temp_conn = StatusNet(config.config['api_path'], auth_type="oauth", consumer_key=api_keys['keys'][instance], consumer_secret=api_keys['secrets'][instance])
                                config.config["consumer_key"] = api_keys['keys'][instance]
                                config.config["consumer_secret"] = api_keys['secrets'][instance]
                        else:
                            temp_conn = StatusNet(config.config['api_path'], auth_type="oauth", consumer_key=oauth_consumer_keys[instance], consumer_secret=oauth_consumer_secrets[instance])
                    else:
                        temp_conn = StatusNet(config.config['api_path'], config.config['username'], config.config['password'])
                except Exception, (errmsg):
                    sys.exit("Couldn't establish connection: %s" % (errmsg))
                print "Okay! Everything seems good! Your new config will now be saved, then IdentiCurse will start properly."
                config.config.save()
        except ValueError, e:
            sys.exit("ERROR: Your config file could not be succesfully loaded due to JSON syntax error(s). Please fix it.\nOriginal error: %s" % (str(e)))

        self.last_page_search = {'query':"", 'occurs':[], 'viewing':0, 'tab':-1}

        # prepare the known commands list
        self.known_commands = [
            "/reply",
            "/favourite",
            "/repeat",
            "/direct",
            "/delete",
            "/profile",
            "/spamreport",
            "/block",
            "/unblock",
            "/user",
            "/context",
            "/subscribe",
            "/unsubscribe",
            "/group",
            "/groupjoin",
            "/groupleave",
            "/groupmember",
            "/tag",
            "/sentdirects",
            "/favourites",
            "/search",
            "/home",
            "/mentions",
            "/directs",
            "/public",
            "/config",
            "/alias",
            "/link",
            "/bugreport",
            "/featurerequest",
            "/quote",
            "/quit",
        ]

        # load all known commands and aliases into the command list
        config.session_store.commands = [command[1:] for command in self.known_commands] + [alias[1:] for alias in config.config["aliases"]]
        
        # Set some defaults for configs that we will always need to use, but that are optional
        if not "enable_colours" in config.config:
            config.config["enable_colours"] = True

        if config.config["enable_colours"]:
            default_colour_scheme = {
                "timelines": ("none", "none"),
                "statusbar": ("black", "white"),
                "tabbar": ("white", "blue"),
                "tabbar_active": ("blue", "white"),
                "selector": ("brown", "none"),
                "time": ("brown", "none"),
                "source": ("green", "none"),
                "notice": ("none", "none"),
                "notice_count": ("blue", "none"),
                "username": ("cyan", "none"),
                "group": ("cyan", "none"),
                "tag": ("cyan", "none"),
                "profile_title": ("cyan", "none"),
                "profile_fields": ("blue", "none"),
                "profile_values": ("none", "none"),
                "search_highlight": ("white", "blue"),
                "notice_link": ("green", "none"),
                "warning": ("black", "red"),
                "pause_line": ("white", "red"),
                "none": ("none", "none")
            }

            # Default colour scheme
            if not "colours" in config.config:
                config.config["colours"] = default_colour_scheme
            else:
                for part in colour_fields:
                    if not part in config.config["colours"]:
                        config.config["colours"][part] = default_colour_scheme[part]

        if not "search_case_sensitive" in config.config:
            config.config['search_case_sensitive'] = "sensitive"
        if not "notify" in config.config:
            config.config['notify'] = "flash"
        if not "long_dent" in config.config:
            config.config['long_dent'] = "split"
        if not "filters" in config.config:
            config.config['filters'] = []
        if not "notice_limit" in config.config:
            config.config['notice_limit'] = 25
        if not "browser" in config.config:
            config.config['browser'] = "xdg-open '%s'"
        if not "border" in config.config:
            config.config['border'] = True
        if not "compact_notices" in config.config:
            config.config['compact_notices'] = False
        if not "user_rainbow" in config.config:
            config.config["user_rainbow"] = False
        if not "group_rainbow" in config.config:
            config.config["group_rainbow"] = False
        if not "tag_rainbow" in config.config:
            config.config["tag_rainbow"] = False
        if not "expand_remote" in config.config:
            config.config["expand_remote"] = False
        if not "smooth_cscroll" in config.config:
            config.config["smooth_cscroll"] = True
        if not "use_oauth" in config.config:
            config.config["use_oauth"] = False
        if not "username" in config.config:
            config.config["username"] = ""
        if not "password" in config.config:
            config.config["password"] = ""
        if not "show_notice_links" in config.config:
            config.config["show_notice_links"] = False
        if not "length_override" in config.config:
            config.config["length_override"] = 0
        if not "prefill_user_cache" in config.config:
            config.config["prefill_user_cache"] = False
        if not "show_source" in config.config:
            config.config["show_source"] = True

        if not "keys" in config.config:
            config.config['keys'] = {}

        if not "tab_complete_mode" in config.config:
            config.config["tab_complete_mode"] = "exact"
        else:
            config.config["tab_complete_mode"] = config.config["tab_complete_mode"].lower()
            if not config.config["tab_complete_mode"] in ["exact", "fuzzy"]:
                config.config["tab_complete_mode"] = "exact"

        if not "ui_order" in config.config:
            config.config['ui_order'] = ["divider", "entry", "divider", "notices", "statusbar", "tabbar"]  # this will recreate the same layout as the old UI

        for ui_item in ["entry", "notices", "statusbar", "tabbar"]:  # ensure no UI element is ommitted by appending any missing ones to the end
            if not ui_item in config.config['ui_order']:
                config.config['ui_order'].append(ui_item)
            while config.config['ui_order'].count(ui_item) > 1:  # if item listed more than once, remove all but the last occurence
                config.config['ui_order'].remove(ui_item)

        keybind_actions = ("firstpage", "newerpage", "olderpage", "refresh",
            "input", "commandinput", "search", "quit", "closetab", "help", "nexttab", "prevtab",
            "qreply", "creply", "cfav", "cunfav", "ccontext", "crepeat", "cnext", "cprev",
            "cfirst", "nextmatch", "prevmatch", "creplymode", "cquote", "tabswapleft", "tabswapright",
            "cdelete", "pausetoggle", "pausetoggleall", "scrollup", "scrolltop", "pageup", "pagedown",
            "scrolldown", "scrollbottom")

        default_keys = {
            "nexttab": [">"],
            "prevtab": ["<"],
            "tabswapright": ["."],
            "tabswapleft": [","],
            "scrollup": [curses.KEY_UP, "k"],
            "scrolltop": [curses.KEY_HOME, "g"],
            "pageup": [curses.KEY_PPAGE, "b"],
            "scrolldown": [curses.KEY_DOWN, "j"],
            "scrollbottom": [curses.KEY_END, "G"],
            "pagedown": [curses.KEY_NPAGE, " "],
            "firstpage": ["="],
            "newerpage": [curses.KEY_LEFT],
            "olderpage": [curses.KEY_RIGHT],
            "refresh": ["r"],
            "input": ["i"],
            "commandinput": [":"],
            "search": ["/"],
            "quit": ["q"],
            "closetab": ["x"],
            "help": ["h"],
            "qreply": ["l"],
            "nextmatch": ["n"],
            "prevmatch": ["N"],
            "cdelete": ["#"],
            "pausetoggleall": ["P"],
            "creply": ["D"],
            "creplymode": ["d"],
            "cnext": ["s"],
            "cprev": ["a"],
            "cfirst": ["z"],
            "cfav": ["f"],
            "cunfav": ["F"],
            "crepeat": ["e"],
            "cquote": ["E"],
            "ccontext": ["c"],
            "pausetoggle": ["p"],
            }

        self.keybindings = {}
        assigned_keys = []

        for action in keybind_actions:
            self.keybindings[action] = []
            if action in config.config['keys']:
                for key in config.config['keys'][action]:
                    if isinstance(key, basestring):
                        key = ord(key)
                    self.keybindings[action].append(key)
                    assigned_keys.append(key)

        for action in keybind_actions:
            if action in default_keys:
                for key in default_keys[action]:
                    if isinstance(key, basestring):
                        key, orig_key = ord(key), key
                    if not key in assigned_keys:
                        self.keybindings[action].append(key)
                    elif len(self.keybindings) == 0:
                        print "WARNING: Tried to assign action '%(action)s' to key '%(key)s', but a user-set keybinding already uses '%(key)s'. This will leave '%(action)s' with no keybindings, so make sure to add a custom binding for '%(action)s' if you still want to use it." % {'action': action, 'key': orig_key}

        try:
            if config.config["use_oauth"]:
                instance = domain_regex.findall(config.config['api_path'])[0][2]
                if "consumer_key" in config.config:
                    self.conn = StatusNet(config.config['api_path'], auth_type="oauth", consumer_key=config.config["consumer_key"], consumer_secret=config.config["consumer_secret"])
                elif not instance in oauth_consumer_keys:
                    print "No suitable consumer keys stored locally, fetching latest list..."
                    req = urllib2.Request("http://identicurse.net/api_keys.json")
                    resp = urllib2.urlopen(req)
                    api_keys = json.loads(resp.read())
                    if not instance in api_keys['keys']:
                        sys.exit("Sorry, IdentiCurse currently lacks the API keys needed to support OAuth with your instance (%(instance)s). If %(instance)s is a public instance, let us know which one it is (filing a bug at http://bugzilla.identicurse.net/ is the preferred way of doing so), and we'll add support as soon as possible." % (locals()))
                    else:
                        self.conn = StatusNet(config.config['api_path'], auth_type="oauth", consumer_key=api_keys['keys'][instance], consumer_secret=api_keys['secrets'][instance])
                        config.config["consumer_key"] = api_keys['keys'][instance]
                        config.config["consumer_secret"] = api_keys['secrets'][instance]
                        config.config.save()
                else:
                    self.conn = StatusNet(config.config['api_path'], auth_type="oauth", consumer_key=oauth_consumer_keys[instance], consumer_secret=oauth_consumer_secrets[instance])
            else:
                self.conn = StatusNet(config.config['api_path'], config.config['username'], config.config['password'])
        except Exception, (errmsg):
            sys.exit("ERROR: Couldn't establish connection: %s" % (errmsg))

        if config.config["prefill_user_cache"]:
            print "Prefilling the user cache based on your followed users. This will take a little while, especially on slower connections. Please be patient."
            users = []
            for user_profile in self.conn.statuses_friends():
                screen_name = user_profile["screen_name"]
                if not screen_name in users:
                    users.append(screen_name)
            for user in users:
                if not hasattr(config.session_store, "user_cache"):
                    config.session_store.user_cache = {}
                config.session_store.user_cache[user] = random.choice(range(8))

        self.insert_mode = False
        self.search_mode = False
        self.quote_mode = False
        self.reply_mode = False
        curses.wrapper(self.initialise)

    def redraw(self):
        self.screen.clear()
        self.screen.refresh()
        self.y, self.x = self.screen.getmaxyx()

        if config.config['border']:
            if self.screen.getmaxyx() == (self.y, self.x):
                self.main_window = self.screen.subwin(self.y-3, self.x-3, 2, 2)
            else:
                return self.redraw()

            self.main_window.box(0, 0)
        else:
            if self.screen.getmaxyx() == (self.y, self.x):
                self.main_window = self.screen.subwin(self.y-1, self.x-1, 1, 1)
            else:
                return self.redraw()
            
        self.main_window.keypad(1)

        y, x = self.main_window.getmaxyx()
        current_y = 0
        if config.config['border']:
            current_y += 3
            y -= 3

        if self.conn.length_limit == 0 and config.config["length_override"] != 0:
            entry_lines = 3
        else:
            if config.config["length_override"] != 0:
                notice_length = config.config["length_override"]
            else:
                notice_length = self.conn.length_limit
            entry_lines = (notice_length / x) + 1

        for part in config.config['ui_order']:
            if part == "divider":
                current_y += 1
            elif part == "entry":
                if config.config['border']:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.entry_window = self.main_window.subwin(entry_lines, x-6, current_y, 5)
                        current_y += entry_lines
                    else:
                        return self.redraw()
                else:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.entry_window = self.main_window.subwin(entry_lines, x-2, current_y, 1)
                        current_y += entry_lines
                    else:
                        return self.redraw()

                self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)

                self.text_entry.stripspaces = 1

            elif part == "notices":
                if config.config['border']:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.notice_window = self.main_window.subwin(y-(entry_lines + 1 + config.config['ui_order'].count("divider")), x-4, current_y, 5)
                        current_y += y - (entry_lines + 1 + config.config['ui_order'].count("divider"))
                    else:
                        return self.redraw()
                else:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.notice_window = self.main_window.subwin(y-(entry_lines + 1 + config.config['ui_order'].count("divider")), x, current_y, 1)
                        current_y += y - (entry_lines + 1 + config.config['ui_order'].count("divider"))
                    else:
                        return self.redraw()

                # I don't like this, but it looks like it has to be done
                if hasattr(self, 'tabs'):
                    for tab in self.tabs:
                        tab.window = self.notice_window

            elif part == "statusbar":
                if config.config['border']:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.status_window = self.main_window.subwin(1, x-5, current_y, 5)
                        current_y += 1
                    else:
                        return self.redraw()
                else:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.status_window = self.main_window.subwin(1, x, current_y, 1)
                        current_y += 1
                    else:
                        return self.redraw()

            elif part == "tabbar":
                if config.config['border']:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.tab_bar_window = self.main_window.subwin(1, x-5, current_y, 5)
                        current_y += 1
                    else:
                        return self.redraw()
                else:
                    if self.screen.getmaxyx() == (self.y, self.x):
                        self.tab_bar_window = self.main_window.subwin(1, x, current_y, 1)
                        current_y += 1
                    else:
                        return self.redraw()

        if hasattr(self, 'status_bar'):
            self.status_bar.window = self.status_window
            self.status_bar.redraw()
        if hasattr(self, 'tab_bar'):
            self.tab_bar.window = self.tab_bar_window

        self.screen.bkgd(" ", curses.color_pair(colour_fields["none"]))
        self.main_window.bkgd(" ", curses.color_pair(colour_fields["none"]))
        self.notice_window.bkgd(" ", curses.color_pair(colour_fields["timelines"]))
        self.status_window.bkgd(" ", curses.color_pair(colour_fields["statusbar"]))
        self.tab_bar_window.bkgd(" ", curses.color_pair(colour_fields["tabbar"]))
        self.screen.refresh()

    def initialise(self, screen):
        self.screen = screen

        try:
            curses.curs_set(0)  # try to hide the cursor. Textbox makes it visible again, then hides it on exit
        except:
            pass

        curses.noecho()
        curses.cbreak()
        curses.use_default_colors()

        if curses.has_colors() and config.config['enable_colours'] == True:
            curses.start_color()

            if "custom_colours" in config.config:
                temp_colours = colours.copy()
                temp_colours.update(config.config['custom_colours'])
                if not curses.can_change_color():
                    raise Exception("Cannot set custom colours, since your terminal does not support changing colour values. Using \"export TERM=xterm-256color\" may resolve this, since some terminals only enable that function when 256 colours are available.")
                elif len(temp_colours) >= curses.COLORS:
                    raise Exception("Cannot set custom colours, since your terminal supports only %d colour slots. Adding all the custom colours defined in your config would need %d slots. For many terminals, using \"export TERM=xterm-256color\" will allow use of 256 slots." % (curses.COLORS, len(temp_colours)))
                else:
                    colour_num = len(colours)
                    for colour_name, colour_value in config.config['custom_colours'].items():
                        if colour_value[0] == "#":
                            colour_value = colour_value[1:]
                        r = int((ord(colour_value[0:2].decode("hex")) * 1000.0) / 255.0)
                        g = int((ord(colour_value[2:4].decode("hex")) * 1000.0) / 255.0)
                        b = int((ord(colour_value[4:6].decode("hex")) * 1000.0) / 255.0)
                        if colour_name in colours:  # if we're redefining an already existing colour
                            curses.init_color(colours[colour_name], r, g, b)
                        else:
                            curses.init_color(colour_num, r, g, b)
                            colours[colour_name] = colour_num
                            colour_num += 1

            for field, (fg, bg) in config.config['colours'].items():
                try:
                    curses.init_pair(colour_fields[field], colours[fg], colours[bg])
                except:
                    continue
            c = 50
            for (key, value) in colours.items():
                if (value + 1) > curses.COLORS:
                    continue

                if not key in ("black", "white", "none") and key != config.config['colours']['notice']:
                    base_colours[colours[key]] = c
                    curses.init_pair(c, value, colours["none"])
                    c += 1
        else:
            for field in colour_fields:
                curses.init_pair(colour_fields[field], -1, -1)

            c = 50
            for (key, value) in colours.items():
                if key != "black":
                    base_colours[colours[key]] = c
                    curses.init_pair(c, -1, -1)
                    c += 1

        self.redraw()

        self.status_bar = StatusBar(self.status_window)
        self.status_bar.update("Welcome to IdentiCurse")
        
        self.tabs = []
        for tabspec in config.config['initial_tabs'].split("|"):
            if tabspec[0] == "@":
                tabspec = "user:" + tabspec[1:]
            elif tabspec[0] == "!":
                tabspec = "group:" + tabspec[1:]
            elif tabspec[0] == "#":
                tabspec = "tag:" + tabspec[1:]
            elif tabspec[0] == "?":
                tabspec = "search:" + tabspec[1:]
            tab = tabspec.split(':')
            if tab[0] in ("home", "mentions", "direct", "public", "sentdirect", "favourites"):
                already_have_one = False
                for tab_obj in self.tabs:  # awkward name, but we already have a tab variable
                    if hasattr(tab_obj, 'timeline_type'):
                        if tab_obj.timeline_type == tab[0]:
                            already_have_one = True
                            break
                if not already_have_one:
                    self.tabs.append(Timeline(self.conn, self.notice_window, tab[0]))
            elif tab[0] == "profile":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                self.tabs.append(Profile(self.conn, self.notice_window, screen_name))
            elif tab[0] == "user":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                user_id = self.conn.users_show(screen_name=screen_name)['id']
                self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'screen_name':screen_name, 'user_id':user_id}))
            elif tab[0] == "group":
                nickname = tab[1]
                if nickname[0] == "!":
                    nickname = nickname[1:]
                group_id = int(self.conn.statusnet_groups_show(nickname=nickname)['id'])
                self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'nickname':nickname, 'group_id':group_id}))
            if tab[0] == "tag":
                tag = tab[1]
                if tag[0] == "#":
                    tag = tag[1:]
                self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}))
            if tab[0] == "search":
                self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':tab[1]}))
            #not too sure why anyone would need to auto-open these last two, but it couldn't hurt to add them
            if tab[0] == "context":
                notice_id = int(tab[1])
                self.tabs.append(Timeline(self.conn, self.notice_window, "context", {'notice_id':notice_id}))
            if tab[0] == "help":
                self.tabs.append(Help(self.notice_window, self.path))

        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

        self.current_tab = 0
        self.tabs[self.current_tab].active = True
        self.tab_order = range(len(self.tabs))

        self.tab_bar = TabBar(self.tab_bar_window)
        self.tab_bar.tabs = [tab.name for tab in self.tabs]
        self.tab_bar.current_tab = self.current_tab
        self.tab_bar.update()
        
        self.update_tabs()
        self.display_current_tab()

        self.loop()

    def update_tabs(self):
        self.update_timer.cancel()
        if self.insert_mode == False:
            self.status_bar.update("Updating Timelines...")
            self.tab_bar.tabs = [tab.name for tab in self.tabs]
            self.tab_bar.current_tab = self.current_tab
            self.tab_bar.update()
            TabUpdater(self.tabs, self, 'end_update_tabs').start()
        else:
            self.update_timer = Timer(config.config['update_interval'], self.update_tabs)

    def end_update_tabs(self):
        self.display_current_tab()
        if config.session_store.update_error is not None:
            self.status_bar.timed_update(config.session_store.update_error)
        self.status_bar.update("Doing nothing.")
        self.tab_bar.tabs = [tab.name for tab in self.tabs]
        self.tab_bar.current_tab = self.current_tab
        self.tab_bar.update()
        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def update_tab_buffers(self):
        for tab in self.tabs:
            tab.update_buffer()

    def display_current_tab(self):
        self.tabs[self.current_tab].display()
        self.tab_bar.tabs = [tab.name for tab in self.tabs]
        self.tab_bar.current_tab = self.current_tab
        self.tab_bar.update()

    def close_current_tab(self):
        if len(self.tabs) == 1:
            pass
        else:
            del self.tabs[self.current_tab]
            del self.tab_order[0]
            for index in range(len(self.tab_order)):
                if self.tab_order[index] > self.current_tab:
                    self.tab_order[index] -= 1
            self.current_tab = self.tab_order[0]
            self.tabs[self.current_tab].active = True
            
            self.display_current_tab()

    def loop(self):
        self.running = True

        while self.running:
            input = self.main_window.getch()
           
            if self.qreply == False:
                switch_to_tab = None
                for x in range(0, len(self.tabs)):
                    if x >= 9:
                        break
                    if input == ord(str(x+1)):
                        switch_to_tab = x
                if input in self.keybindings['nexttab']:
                    if self.current_tab < (len(self.tabs) - 1):
                        switch_to_tab = self.current_tab + 1
                elif input in self.keybindings['prevtab']:
                    if self.current_tab >= 1:
                        switch_to_tab = self.current_tab - 1
                elif input in self.keybindings['tabswapright']:
                    if self.current_tab < (len(self.tabs) - 1):
                        self.tabs[self.current_tab], self.tabs[self.current_tab+1] = self.tabs[self.current_tab+1], self.tabs[self.current_tab]
                        switch_to_tab = self.current_tab + 1
                elif input in self.keybindings['tabswapleft']:
                    if self.current_tab >= 1:
                        self.tabs[self.current_tab-1], self.tabs[self.current_tab] = self.tabs[self.current_tab], self.tabs[self.current_tab-1]
                        switch_to_tab = self.current_tab - 1

                if switch_to_tab is not None:
                    self.tab_order.insert(0, self.tab_order.pop(self.tab_order.index(switch_to_tab)))
                    self.tabs[self.current_tab].active = False
                    self.current_tab = switch_to_tab
                    self.tabs[self.current_tab].active = True
            else:
                for x in range(1, 9):
                    if input == ord(str(x)):
                        self.update_timer.cancel()
                        self.insert_mode = True
                        self.parse_input(self.text_entry.edit("/r " + str(x) + " "))
                self.qreply = False
            
            if input in self.keybindings['scrollup']:
                self.tabs[self.current_tab].scrollup(1)
                self.display_current_tab()
            elif input in self.keybindings['scrolltop']:
                self.tabs[self.current_tab].scrollup(0)
                self.display_current_tab()
            elif input in self.keybindings['pageup']:
                self.tabs[self.current_tab].scrollup(self.main_window.getmaxyx()[0] - 11) # the 11 offset gives 2 lines of overlap between the pre-scroll view and post-scroll view
                self.display_current_tab()
            elif input in self.keybindings['scrolldown']:
                self.tabs[self.current_tab].scrolldown(1)
                self.display_current_tab()
            elif input in self.keybindings['scrollbottom']:
                self.tabs[self.current_tab].scrolldown(0)
                self.display_current_tab()
            elif input in self.keybindings['pagedown']:
                self.tabs[self.current_tab].scrolldown(self.main_window.getmaxyx()[0] - 11) # as above
                self.display_current_tab()
            elif input in self.keybindings['firstpage']:
                if self.tabs[self.current_tab].prevpage(0):
                    self.status_bar.update("Moving to first page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input in self.keybindings['newerpage']:
                if self.tabs[self.current_tab].prevpage():
                    self.status_bar.update("Moving to newer page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input in self.keybindings['olderpage']:
                if self.tabs[self.current_tab].nextpage():
                    self.status_bar.update("Moving to older page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input in self.keybindings['refresh']:
                self.update_tabs()
            elif input in self.keybindings['input']:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit())
            elif input in self.keybindings['commandinput']:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit("/"))
            elif input in self.keybindings['search']:
                self.update_timer.cancel()
                self.insert_mode = True
                self.search_mode = True
                self.parse_search(self.text_entry.edit())
            elif input in self.keybindings['quit']:
                self.running = False
            elif input in self.keybindings['closetab']:
                self.close_current_tab()
            elif input in self.keybindings['help']:
                self.tabs.append(Help(self.notice_window, self.path))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
            elif input in self.keybindings['qreply']:
                self.qreply = True
            elif input in self.keybindings['nextmatch']:
                if (self.last_page_search['query'] != "") and (self.last_page_search['tab'] == self.current_tab):
                    if self.last_page_search['viewing'] < (len(self.last_page_search['occurs']) - 1):
                        self.last_page_search['viewing'] += 1
                    else:
                        self.last_page_search['viewing'] = 0
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    if self.last_page_search['viewing'] == 0:
                        self.status_bar.update("Viewing result #%d for '%s' (search hit BOTTOM, continuing at TOP)" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    else:
                        self.status_bar.update("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    self.display_current_tab()
            elif input in self.keybindings['prevmatch']:
                if (self.last_page_search['query'] != "") and (self.last_page_search['tab'] == self.current_tab):
                    if self.last_page_search['viewing'] > 0:
                        self.last_page_search['viewing'] -= 1
                    else:
                        self.last_page_search['viewing'] = len(self.last_page_search['occurs']) - 1
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    if self.last_page_search['viewing'] == (len(self.last_page_search['occurs']) - 1):
                        self.status_bar.update("Viewing result #%d for '%s' (search hit TOP, continuing at BOTTOM)" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    else:
                        self.status_bar.update("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, self.last_page_search['query']))
                    self.display_current_tab()
            elif input in self.keybindings['cdelete']:
                self.cmd_delete(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
            elif input == curses.ascii.ctrl(ord("l")):
                self.redraw()
            elif input in self.keybindings['pausetoggleall']:
                for tab in self.tabs:
                    if hasattr(tab, "timeline"):
                        tab.paused = not tab.paused
                        if tab.paused and (len(tab.timeline) > 0):
                            self.tabs[self.current_tab].timeline[0]["ic__paused_on"] = True
                        tab.update_buffer()
                        tab.update_name()
                self.tab_bar.tabs = [tab.name for tab in self.tabs]
                self.tab_bar.current_tab = self.current_tab
                self.tab_bar.update()
            # and now the c* actions, and anything else that shouldn't run on non-timeline tabs
            if isinstance(self.tabs[self.current_tab], Timeline) and len(self.tabs[self.current_tab].timeline) > 0:  # don't try to do the c* actions unless on a populated timeline
                if (self.tabs[self.current_tab].chosen_one + 1) > len(self.tabs[self.current_tab].timeline):  # reduce chosen_one if it's beyond the end
                    self.tabs[self.current_tab].chosen_one = len(self.tabs[self.current_tab].timeline) - 1
                    self.tabs[self.current_tab].update_buffer()

                if input in self.keybindings['creply']:
                    self.update_timer.cancel()
                    self.insert_mode = True
                    if "direct" in self.tabs[self.current_tab].timeline_type:
                        self.parse_input(self.text_entry.edit("/dm " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
                    else:
                        self.parse_input(self.text_entry.edit("/r " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
                elif input in self.keybindings['creplymode']:
                    self.update_timer.cancel()
                    if "direct" in self.tabs[self.current_tab].timeline_type:
                        self.insert_mode = True
                        self.parse_input(self.text_entry.edit("/dm " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
                    else:
                        try:
                            self.cmd_reply(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                        except Exception, (errmsg):
                            self.status_bar.timed_update("ERROR: Couldn't post status: %s" % (errmsg))
                elif input in self.keybindings['cnext']:
                    if self.tabs[self.current_tab].chosen_one != (len(self.tabs[self.current_tab].timeline) - 1):
                        self.tabs[self.current_tab].chosen_one += 1
                        self.tabs[self.current_tab].update_buffer()
                        self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one, smooth_scroll=config.config["smooth_cscroll"])
                elif input in self.keybindings['cprev']:
                    if self.tabs[self.current_tab].chosen_one != 0:
                        self.tabs[self.current_tab].chosen_one -= 1
                        self.tabs[self.current_tab].update_buffer()
                        self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one, smooth_scroll=config.config["smooth_cscroll"])
                elif input in self.keybindings['cfirst']:
                    if self.tabs[self.current_tab].chosen_one != 0:
                        self.tabs[self.current_tab].chosen_one = 0
                        self.tabs[self.current_tab].update_buffer()
                        self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
                elif input in self.keybindings['cfav']:
                    self.cmd_favourite(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                elif input in self.keybindings['cunfav']:
                    self.cmd_unfavourite(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                elif input in self.keybindings['crepeat']:
                    can_repeat = True
                    try:
                        if self.tabs[self.current_tab].timeline_type in ["direct", "sentdirect"]:
                            can_repeat = False
                    except AttributeError:
                        pass  # we must be in a Context tab, so repeating is fine.
                    if can_repeat:
                        self.cmd_repeat(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                elif input in self.keybindings['cquote']:
                    can_repeat = True
                    try:
                        if self.tabs[self.current_tab].timeline_type in ["direct", "sentdirect"]:
                            can_repeat = False
                    except AttributeError:
                        pass  # we must be in a Context tab, so repeating is fine.
                    if can_repeat:
                        self.update_timer.cancel()
                        self.cmd_quote(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                elif input in self.keybindings['ccontext']:
                    self.cmd_context(self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one])
                elif input in self.keybindings['pausetoggle']:
                    self.tabs[self.current_tab].paused = not self.tabs[self.current_tab].paused
                    if self.tabs[self.current_tab].paused and (len(self.tabs[self.current_tab].timeline) > 0):
                        self.tabs[self.current_tab].timeline[0]["ic__paused_on"] = True
                    self.tabs[self.current_tab].update_buffer()  # get the pauseline drawn
                    self.tabs[self.current_tab].update_name()  # force the tab names to update
                    self.tab_bar.tabs = [tab.name for tab in self.tabs]
                    self.tab_bar.current_tab = self.current_tab
                    self.tab_bar.update()


            y, x = self.screen.getmaxyx()
            if y != self.y or x != self.x:
                self.redraw()
                self.update_tab_buffers()


            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, param):
        if type(param) == type([]):
            guess_list = param
            self.status_bar.timed_update("  ".join(guess_list), 2)
        else:
            character_count = param
            if self.quote_mode:
                if self.conn.length_limit == 0:
                    self.status_bar.update("Quote Mode: " + str(character_count))
                else:
                    self.status_bar.update("Quote Mode: " + str(self.conn.length_limit - character_count))
            elif self.reply_mode:
                if self.conn.length_limit == 0:
                    self.status_bar.update("Reply Mode: " + str(character_count))
                else:
                    self.status_bar.update("Reply Mode: " + str(self.conn.length_limit - character_count))
            elif self.search_mode:
                if self.last_page_search['query'] != "":
                    self.status_bar.update("In-page Search (last search: '%s')" % (self.last_page_search['query']))
                else:
                    self.status_bar.update("In-page Search")
            else:
                if self.conn.length_limit == 0:
                    self.status_bar.update("Insert Mode: " + str(character_count))
                else:
                    self.status_bar.update("Insert Mode: " + str(self.conn.length_limit - character_count))

    def parse_input(self, input):
        update = False
        new_tab = False

        if input is None:
            input = ""

        if len(input) > 0:      # don't do anything if the user didn't enter anything
            input = input.rstrip()

            tokens = [token for token in input.split(" ") if token != ""]

            if tokens[0][0] == "i" and ((tokens[0][1:] in self.known_commands) or (tokens[0][1:] in config.config["aliases"])):
                tokens[0] = tokens[0][1:]  # avoid doing the wrong thing when people accidentally submit stuff like "i/r 2 blabla"

            for command in self.known_commands:
                # catch mistakes like "/r1" - the last condition is so that, for example, "/directs" is not mistakenly converted to "/direct s"
                if (tokens[0][:len(command)] == command) and (tokens[0] != command) and not (tokens[0] in self.known_commands) and not (tokens[0] in config.config['aliases']):
                    tokens[:1] = [command, tokens[0].replace(command, "")]
                # catch mis-capitalizations
                if tokens[0].lower() == command.lower() and not tokens[0].lower() in [cmd.lower() for cmd in self.known_commands if cmd != command]:
                    tokens[0] = command
            for alias in config.config['aliases']:
                # catch mistakes like "/r1" - the last condition is so that, for example, "/directs" is not mistakenly converted to "/direct s"
                if (tokens[0][:len(alias)] == alias) and (tokens[0] != alias) and not (tokens[0] in self.known_commands) and not (tokens[0] in config.config['aliases']):
                    tokens[:1] = [alias, tokens[0].replace(alias, "")]
                # catch mis-capitalizations
                if tokens[0].lower() == alias.lower() and not tokens[0].lower() in [als.lower() for als in config.config['aliases'] if als != alias]:
                    tokens[0] = alias

            if tokens[0] in config.config["aliases"]:
                tokens = config.config["aliases"][tokens[0]].split(" ") + tokens[1:]

            try:
                if ("direct" in self.tabs[self.current_tab].timeline_type) and (tokens[0] == "/reply"):
                    tokens[0] = "/direct"
            except AttributeError:
                # the tab has no timeline_type, so it's *definitely* not directs.
                pass

            if tokens[0] in self.known_commands:
                
                try:
                    if tokens[0] == "/reply" and len(tokens) >= 2:
                        self.status_bar.update("Posting Reply...")
    
                        try:
                            try:
                                float(tokens[1])
                            except ValueError:
                                user = tokens[1]
                                if user[0] == "@":
                                        user = user[1:]
                                update = self.cmd_mention(user, " ".join(tokens[2:]))
                            else:
                                update = self.cmd_reply(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1], " ".join(tokens[2:]))
                        except Exception, (errmsg):
                            self.status_bar.timed_update("ERROR: Couldn't post status: %s" % (errmsg))
    
                    elif tokens[0] == "/favourite" and len(tokens) == 2:
                        self.cmd_favourite(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])
    
                    elif tokens[0] == "/unfavourite" and len(tokens) == 2:
                        self.cmd_unfavourite(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])
    
                    elif tokens[0] == "/repeat" and len(tokens) == 2:
                        update = self.cmd_repeat(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])
                        
                    elif tokens[0] == "/direct" and len(tokens) >= 3:
                        try:
                            float(tokens[1])
                        except ValueError:
                            screen_name = tokens[1]
                            if screen_name[0] == "@":
                                screen_name = screen_name[1:]
                        else:
                            if "direct" in self.tabs[self.current_tab].timeline_type:
                                screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['sender']['screen_name']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['user']['screen_name']
                                else:
                                    screen_name = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['screen_name']
                        self.cmd_direct(screen_name, " ".join(tokens[2:]))
    
                    elif tokens[0] == "/delete" and len(tokens) == 2:
                        self.cmd_delete(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])
    
                    elif tokens[0] == "/profile" and len(tokens) == 2:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        self.cmd_profile(user)
    
                    elif tokens[0] == "/spamreport" and len(tokens) >= 3:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            username = tokens[1]
                            if username[0] == "@":
                                    username = username[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        update = self.cmd_spamreport(username, " ".join(tokens[2:]))
    
                    elif tokens[0] == "/block" and len(tokens) >= 2:
                        for token in tokens[1:]:
                            # Yeuch
                            try:
                                float(token)
                            except ValueError:
                                user = token
                                if user[0] == "@":
                                    user = user[1:]
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                            self.cmd_block(user)
    
                    elif tokens[0] == "/unblock" and len(tokens) >= 2:
                        self.status_bar.update("Removing Block(s)...")
                        for token in tokens[1:]:
                            # Yeuch
                            try:
                                float(token)
                            except ValueError:
                                user = token
                                if user[0] == "@":
                                    user = user[1:]
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                            self.cmd_unblock(user)
    
                    elif tokens[0] == "/user" and len(tokens) == 2:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                user = user[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                        
                        self.cmd_user(user)
    
                    elif tokens[0] == "/context" and len(tokens) == 2:
                            self.cmd_context(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])
    
                    elif tokens[0] == "/subscribe" and len(tokens) == 2:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                        self.cmd_subscribe(user)
                        
                    elif tokens[0] == "/unsubscribe" and len(tokens) == 2:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                        self.cmd_unsubscribe(user)
    
                    elif tokens[0] == "/group" and len(tokens) == 2:
                        self.status_bar.update("Loading Group Timeline...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        self.cmd_group(group)
    
                    elif tokens[0] == "/groupjoin" and len(tokens) == 2:
                        self.status_bar.update("Joining Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        self.cmd_groupjoin(group)
    
                    elif tokens[0] == "/groupleave" and len(tokens) == 2:
                        self.status_bar.update("Leaving Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        self.cmd_groupleave(group)
    
                    elif tokens[0] == "/groupmember" and len(tokens) == 2:
                        self.status_bar.update("Checking membership...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        self.cmd_groupmember(group)

                    elif tokens[0] == "/tag" and len(tokens) == 2:
                        self.status_bar.update("Loading Tag Timeline...")
                        tag = tokens[1]
                        if tag[0] == "#":
                            tag = tag[1:]
                        self.cmd_tag(tag)
    
                    elif tokens[0] == "/sentdirects" and len(tokens) == 1:
                        self.cmd_sentdirects()                            
    
                    elif tokens[0] == "/favourites" and len(tokens) == 1:
                        self.cmd_favourites()
                        
                    elif tokens[0] == "/search" and len(tokens) >= 2:
                        query = " ".join(tokens[1:])
                        self.cmd_search(query)
                    
                    elif tokens[0] == "/home" and len(tokens) == 1:
                        self.cmd_home()
                    
                    elif tokens[0] == "/mentions" and len(tokens) == 1:
                        self.cmd_mentions()
                    
                    elif tokens[0] == "/directs" and len(tokens) == 1:
                        self.cmd_directs()
                    
                    elif tokens[0] == "/public" and len(tokens) == 1:
                        self.cmd_public()
                        
                    elif tokens[0] == "/config" and len(tokens) >= 3:
                        self.cmd_config(tokens[1], " ".join(tokens[2:]))
    
                    elif tokens[0] == "/alias" and len(tokens) >= 3:
                        self.cmd_alias(tokens[1], " ".join(tokens[2:]))

                    elif tokens[0] == "/link" and len(tokens) >= 2:
                        if len(tokens) == 2:  # only notice number given, assume first link
                            self.cmd_link(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1], 1)
                        else:  # notice number and link number given
                            self.cmd_link(self.tabs[self.current_tab].timeline[int(tokens[2]) - 1], tokens[1])

                    elif tokens[0] == "/bugreport" and len(tokens) >= 2:
                        update = self.cmd_bugreport(" ".join(tokens[1:]))
   
                    elif tokens[0] == "/featurerequest" and len(tokens) >= 2:
                        update = self.cmd_featurerequest(" ".join(tokens[1:]))

                    elif tokens[0] == "/quote" and len(tokens) == 2:
                        update = self.cmd_quote(self.tabs[self.current_tab].timeline[int(tokens[1]) - 1])

                    elif tokens[0] == "/quit" and len(tokens) == 1:
                        self.running = False
   
                except StatusNetError, e:
                    self.status_bar.timed_update("Status.Net error %d: %s" % (e.errcode, e.details))
            else:
                try:
                    update = self.cmd_post(input)
                except StatusNetError, e:
                    self.status_bar.timed_update("Status.Net error %d: %s" % (e.errcode, e.details))

            if not update:
                self.tabs[self.current_tab].update()
                self.status_bar.update("Doing nothing.")

        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.tabs[self.current_tab].search_highlight_line = -1
        self.display_current_tab()
        self.status_bar.update("Doing nothing.")
        self.insert_mode = False
        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def opens_tab(fail_on_exists=None):  # decorator factory, creates decorators to deal with the standard switching to tab stuff
        def tabopen_decorator(cmd):
            def outcmd(*largs, **kargs):
                self = largs[0]
                already_have_one = False
                if fail_on_exists is not None:
                    for tab in self.tabs:
                        if hasattr(tab, "timeline_type") and tab.timeline_type == fail_on_exists:
                            already_have_one = True
                            break
                if not already_have_one:
                    self.tabs.append(cmd(*largs, **kargs))
                    self.tabs[self.current_tab].active = False
                    self.current_tab = len(self.tabs) - 1
                    self.tabs[self.current_tab].active = True
                    self.tab_order.insert(0, self.current_tab)
                    self.tabs[self.current_tab].update()
                return True
            return outcmd
        return tabopen_decorator

    def shows_status(status_msg):  # decorator factory, creates status decorators for commands that show statuses
        def status_decorator(cmd):
            def outcmd(*largs, **kargs):
                self = largs[0]
                self.status_bar.update(status_msg + "...")
                retval = cmd(*largs, **kargs)
                self.status_bar.update("Doing nothing.")
                return retval
            return outcmd
        return status_decorator

    def posts_notice(cmd):  # decorator which inserts the newly-posted notice(s) for commands that post
        def outcmd(*largs, **kargs):
            self = largs[0]
            update = cmd(*largs, **kargs)
            if update is not None:
                update["ic__raw_datetime"] = helpers.notice_datetime(update)
                update["ic__from_web"] = False
                if self.tabs[self.current_tab].name == "Context":  # if we're in a context tab, add notice to there too
                    self.tabs[self.current_tab].timeline.insert(0, update)
                    self.tabs[self.current_tab].update_buffer()
                for tab in self.tabs:
                    if not hasattr(tab, 'timeline_type'):
                        continue
                    if tab.timeline_type == "home":
                        if isinstance(update, list):
                            for notice in update:
                                tab.timeline.insert(0, notice)
                        else:
                            tab.timeline.insert(0, update)
                        tab.update_buffer()
            self.status_bar.update("Doing nothing.")
            return True
        return outcmd

    def repeat_passthrough(cmd):  # decorator which unpacks repeats for any commands that should handle only the original notice
        def outcmd(*largs, **kargs):  # requires that notice is the *second* argument, for now at least
            largs = list(largs)  # largs is a tuple, we need it mutable
            if "retweeted_status" in largs[1]:
                largs[1] = largs[1]["retweeted_status"]
            return cmd(*largs, **kargs)
        return outcmd

    @shows_status("Posting reply")
    @posts_notice
    @repeat_passthrough
    def cmd_reply(self, notice, message=""):
        user = notice["user"]["screen_name"]
        if message == "":
            self.reply_mode = True
            status = self.text_entry.edit("@%s " % (user))
            self.reply_mode = False
        else:
            status = "@%s %s" % (notice["user"]["screen_name"], message)
        if status is None:
            status = ""
        if len(status) > 0:
            return self.conn.statuses_update(status, "IdentiCurse", int(notice["id"]), long_dent=config.config["long_dent"], dup_first_word=True)

    @shows_status("Posting mention")
    @posts_notice
    def cmd_mention(self, username, message):
        status = "@%s %s" % (username, message)
        return self.conn.statuses_update(status, "IdentiCurse", long_dent=config.config["long_dent"], dup_first_word=True)

    @shows_status("Posting notice")
    @posts_notice
    def cmd_post(self, message):
        if message is None:
            message = ""
        if len(message) > 0:
            return self.conn.statuses_update(message, "IdentiCurse", long_dent=config.config["long_dent"], dup_first_word=False)

    @shows_status("Favouriting notice")
    @repeat_passthrough
    def cmd_favourite(self, notice):
        self.conn.favorites_create(notice["id"]) 

    @shows_status("Unfavouriting notice")
    @repeat_passthrough
    def cmd_unfavourite(self, notice):
        self.conn.favorites_destroy(notice["id"]) 

    @shows_status("Repeating notice")
    @posts_notice
    @repeat_passthrough
    def cmd_repeat(self, notice):
        return self.conn.statuses_retweet(notice["id"], source="IdentiCurse")

    @shows_status("Quoting notice")
    @posts_notice
    @repeat_passthrough
    def cmd_quote(self, notice):
        self.quote_mode = True
        new_status_base_unclean = "RD @%s %s" % (notice['user']['screen_name'], notice['text'])
        new_status_base_clean = ""
        for entity in helpers.split_entities(new_status_base_unclean):
            if entity['type'] == "group":
                entity['text'] = "#" + entity['text'][1:]
            new_status_base_clean += entity['text']
        status = self.text_entry.edit(new_status_base_clean)
        self.quote_mode = False

        if status is None:
            status = ""
        if len(status) > 0:
            return self.conn.statuses_update(status, "IdentiCurse", int(notice["id"]), long_dent=config.config["long_dent"], dup_first_word=False)

    @shows_status("Sending direct message")
    def cmd_direct(self, username, message):
        user_id = self.conn.users_show(screen_name=username)['id']
        self.conn.direct_messages_new(username, user_id, message, source="IdentiCurse")

    @shows_status("Deleting notice")
    def cmd_delete(self, notice):
        delete_succeeded = False
        try:
            self.conn.statuses_destroy(notice["id"])
            delete_succeeded = True
        except StatusNetError, e:
            if e.errcode == 403:
                if "retweeted_status" in notice:  # user doesn't own the repeat, so is probably trying to delete the original status
                    self.conn.statuses_destroy(notice["retweeted_status"]["id"])
                    delete_succeeded = True
                else:  # user is trying to delete something they don't own. the API doesn't like this
                    self.status_bar.timed_update("You cannot delete others' notices.", 3)
            else:  # it wasn't a 403, so re-raise
                raise(e)
        try:
            self.conn.statuses_destroy(notice["id"])  # for now, we try it twice, since identi.ca at least seems to have an issue where deleting must be done twice
        except:
            pass  # since we should've already got it (in an ideal situation), ignore the errors from this attempt.
        if delete_succeeded:
            for tab in [tab for tab in self.tabs if hasattr(tab, "timeline_type")]:
                n_id = notice["id"]  # keep this in a variable of it's own, so deleting the original notice doesn't break the test in the next bit
                for tl_notice in tab.timeline:
                    if tl_notice["id"] == n_id:
                        tab.timeline.remove(tl_notice)
                tab.update_buffer()

    @shows_status("Loading profile")
    @opens_tab()
    def cmd_profile(self, username):
        return Profile(self.conn, self.notice_window, username)

    @shows_status("Deploying orbital nukes")
    @posts_notice
    def cmd_spamreport(self, username, reason=""):
        target_user_id = self.conn.users_show(screen_name=username)["id"]
        status = "@support !sr %s UID %d" % (username, target_user_id)
        if len(reason) > 0:
            status += " %s" % (reason)
        user_id = self.conn.users_show()['id']
        group_id = self.conn.statusnet_groups_show(nickname="spamreport")['id']
        if not self.conn.statusnet_groups_is_member(user_id, group_id):
            self.status_bar.timed_update("You are not a member of the !spamreport group. Joining it is highly recommended if reporting spam.")
        self.conn.blocks_create(user_id=target_user_id, screen_name=username)
        return self.conn.statuses_update(status, "IdentiCurse")

    @shows_status("Blocking user")
    def cmd_block(self, username):
        user_id = self.conn.users_show(screen_name=username)["id"]
        self.conn.blocks_create(user_id=user_id, screen_name=username)

    @shows_status("Unblocking user")
    def cmd_unblock(self, username):
        user_id = self.conn.users_show(screen_name=username)["id"]
        self.conn.blocks_destroy(user_id=user_id, screen_name=username)

    @shows_status("Loading user timeline")
    @opens_tab()
    def cmd_user(self, username):
        user_id = self.conn.users_show(screen_name=username)["id"]
        return Timeline(self.conn, self.notice_window, "user", {'user_id':user_id, 'screen_name':username})

    @shows_status("Loading group timeline")
    @opens_tab()
    def cmd_group(self, group):
        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
        return Timeline(self.conn, self.notice_window, "group", {'group_id':group_id, 'nickname':group})

    @shows_status("Loading tag timeline")
    @opens_tab()
    def cmd_tag(self, tag):
        return Timeline(self.conn, self.notice_window, "tag", {'tag':tag})

    @shows_status("Loading context")
    @opens_tab()
    @repeat_passthrough
    def cmd_context(self, notice):
        return Timeline(self.conn, self.notice_window, "context", {'notice_id':notice['id']})

    @shows_status("Subscribing to user")
    def cmd_subscribe(self, username):
        user_id = self.conn.users_show(screen_name=username)["id"]
        self.conn.friendships_create(user_id=user_id, screen_name=username)

    @shows_status("Unsubscribing from user")
    def cmd_unsubscribe(self, username):
        user_id = self.conn.users_show(screen_name=username)["id"]
        self.conn.friendships_destroy(user_id=user_id, screen_name=username)

    @shows_status("Joining group")
    def cmd_groupjoin(self, group):
        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
        self.conn.statusnet_groups_join(group_id=group_id, nickname=group)

    @shows_status("Leaving group")
    def cmd_groupleave(self, group):
        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
        self.conn.statusnet_groups_leave(group_id=group_id, nickname=group)

    @shows_status("Checking if you are a member of that group")
    def cmd_groupmember(self, group):
        user_id = self.conn.users_show()['id']
        group_id = self.conn.statusnet_groups_show(nickname=group)['id']
        if self.conn.statusnet_groups_is_member(user_id, group_id):
            self.status_bar.timed_update("You are a member of !%s." % (group))
        else:
            self.status_bar.timed_update("You are not a member of !%s." % (group))

    @shows_status("Loading received direct messages")
    @opens_tab("direct")
    def cmd_directs(self):
        return Timeline(self.conn, self.notice_window, "direct")

    @shows_status("Loading sent direct messages")
    @opens_tab("sentdirect")
    def cmd_sentdirects(self):
        return Timeline(self.conn, self.notice_window, "sentdirect")

    @shows_status("Loading favourites")
    @opens_tab("favourites")
    def cmd_favourites(self):
        return Timeline(self.conn, self.notice_window, "favourites")

    @shows_status("Searching")
    @opens_tab()
    def cmd_search(self, query):
        return Timeline(self.conn, self.notice_window, "search", type_params={'query':query})

    @shows_status("Loading home timeline")
    @opens_tab("home")
    def cmd_home(self):
        return Timeline(self.conn, self.notice_window, "home")

    @shows_status("Loading mentions timeline")
    @opens_tab("mentions")
    def cmd_mentions(self):
        return Timeline(self.conn, self.notice_window, "mentions")

    @shows_status("Loading public timeline")
    @opens_tab("public")
    def cmd_public(self):
        return Timeline(self.conn, self.notice_window, "public")

    @shows_status("Changing config")
    def cmd_config(self, key, value):
        key = key.split('.')
        if len(key) == 2:      # there has to be a clean way to avoid hardcoded len checks, but I can't think what right now, and technically it works for all currently valid config keys
            config.config[key[0]][key[1]] = value
        else:
            config.config[key[0]] = value
        config.config.save()

    @shows_status("Aliasing command")
    def cmd_alias(self, alias, command):
        if alias[0] != "/":
            alias = "/" + alias
        if command[0] != "/":
            command = "/" + command
        config.config["aliases"][alias] = command
        config.config.save()

    @shows_status("Opening link(s)")
    @repeat_passthrough
    def cmd_link(self, notice, link_num):
        links_to_open = []
        if link_num == "*":
            for target_url in helpers.url_regex.findall(notice["text"]):
                if not target_url in links_to_open:
                    links_to_open.append(target_url)
        else:
            link_index = int(link_num) - 1
            target_url = helpers.url_regex.findall(notice["text"])[link_index]
            if not target_url in links_to_open:
                links_to_open.append(target_url)
        for link in links_to_open:
            subprocess.Popen(config.config['browser'] % (link), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    @shows_status("Sending bug report")
    @posts_notice
    def cmd_bugreport(self, report):
        status = "#icursebug " + report
        return self.conn.statuses_update(status, "IdentiCurse", long_dent=config.config['long_dent'], dup_first_word=True)

    @shows_status("Sending feature request")
    @posts_notice
    def cmd_featurerequest(self, request):
        status = "#icurserequest " + request
        return self.conn.statuses_update(status, "IdentiCurse", long_dent=config.config['long_dent'], dup_first_word=True)

    @shows_status("Quitting")
    def cmd_quit(self):
        self.running = False

    def parse_search(self, query):
        if query is not None:
            query = query.rstrip()
            if query == "":
                query = self.last_page_search['query']
            if (self.last_page_search['query'] == query) and not (query == "") and (self.last_page_search['tab'] == self.current_tab):
                # this is a continued search
                if self.last_page_search['viewing'] < (len(self.last_page_search['occurs']) - 1):
                    self.last_page_search['viewing'] += 1
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.tabs[self.current_tab].search_highlight_line = self.last_page_search['occurs'][self.last_page_search['viewing']]
                    self.status_bar.update("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, query))
                    self.display_current_tab()
                else:
                    self.tabs[self.current_tab].search_highlight_line = -1
                    self.status_bar.update("No more results for '%s'" % (query))
            else:
                # new search
                maxx = self.tabs[self.current_tab].window.getmaxyx()[1]
                search_buffer = self.tabs[self.current_tab].buffer.reflowed(maxx - 2)

                page_search = {'query':query, 'occurs':[], 'viewing':0, 'tab':self.current_tab}
                
                for line_index in range(len(search_buffer)):
                    match_found = False
                    for block in search_buffer[line_index]:
                        if config.config['search_case_sensitive'] == "sensitive":
                            if query in block[0]:
                                match_found = True
                                break
                        else:
                            if query.upper() in block[0].upper():
                                match_found = True
                                break
                    if match_found:
                        page_search['occurs'].append(line_index)

                if len(page_search['occurs']) > 0:
                    self.tabs[self.current_tab].scrollto(page_search['occurs'][0])
                    self.tabs[self.current_tab].search_highlight_line = page_search['occurs'][0]
                    self.status_bar.update("Viewing result #1 for '%s'" % (query))
                    self.last_page_search = page_search  # keep this search
                else:
                    self.tabs[self.current_tab].search_highlight_line = -1
                    self.status_bar.update("No results for '%s'" % (query))
                    self.last_page_search = {'query':"", 'occurs':[], 'viewing':0, 'tab':-1}  # reset to no search
        else:
            self.status_bar.update("Doing nothing.")

        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.display_current_tab()
        self.insert_mode = False
        self.search_mode = False
        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def quit(self):
        try:
            self.update_timer.cancel()
        except ValueError:  # it may already have been cancelled if it fired shortly before we quit, in which case we can't end it
            pass
        curses.endwin()
        sys.exit()
