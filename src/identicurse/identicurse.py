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

import os, sys, curses, locale, re, subprocess
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
}

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
        self.path = os.path.dirname(os.path.realpath( __file__ ))
        self.qreply = False
        
        if "config_filename" in additional_config:
            config.config.filename = os.path.expanduser(additional_config['config_filename'])
        else:
            config.config.filename = os.path.join(os.path.expanduser("~") ,".identicurse")

        try:
            if os.path.exists(config.config.filename) or os.path.exists(os.path.join("/etc", "identicurse.conf")):
                if not config.config.load():
                    config.config.load(os.path.join("/etc", "identicurse.conf"))
            else:
                import getpass, time
                # no config yet, so let's build one
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
        except ValueError:
            sys.exit("ERROR: Your config file could not be succesfully loaded due to JSON syntax error(s). Please fix it.")

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
            "/quote"
        ]
        
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
            config.config['compact_notices'] = True
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
        if not "keys" in config.config:
            config.config['keys'] = {}
        if not "scrollup" in config.config['keys']:
            config.config['keys']['scrollup'] = ['k']
        if not "scrolltop" in config.config['keys']:
            config.config['keys']['scrolltop'] = ['g']
        if not "pageup" in config.config['keys']:
            config.config['keys']['pageup'] = ['b']
        if not "scrolldown" in config.config['keys']:
            config.config['keys']['scrolldown'] = ['j']
        if not "scrollbottom" in config.config['keys']:
            config.config['keys']['scrollbottom'] = ['G']
        if not "pagedown" in config.config['keys']:
            config.config['keys']['pagedown'] = [' ']

        if not "ui_order" in config.config:
            config.config['ui_order'] = ["divider", "entry", "divider", "notices", "statusbar", "tabbar"]  # this will recreate the same layout as the old UI

        for ui_item in ["entry", "notices", "statusbar", "tabbar"]:  # ensure no UI element is ommitted by appending any missing ones to the end
            if not ui_item in config.config['ui_order']:
                config.config['ui_order'].append(ui_item)
            while config.config['ui_order'].count(ui_item) > 1:  # if item listed more than once, remove all but the last occurence
                config.config['ui_order'].remove(ui_item)

        empty_default_keys = ("firstpage", "newerpage", "olderpage", "refresh",
            "input", "commandinput", "search", "quit", "closetab", "help", "nexttab", "prevtab",
            "qreply", "creply", "cfav", "ccontext", "crepeat", "cnext", "cprev",
            "cfirst", "nextmatch", "prevmatch")

        for k in empty_default_keys:
            config.config['keys'][k] = []
        
        self.url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

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
                        sys.exit("Sorry, IdentiCurse currently lacks the API keys needed to support OAuth with your instance (%(instance)s). If %(instance)s is a public instance, let us know which one it is, and we'll add support as soon as possible." % (locals()))
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

        self.insert_mode = False
        self.search_mode = False
        self.quote_mode = False
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

        if self.conn.length_limit == 0:
            entry_lines = 3
        else:
            entry_lines = (self.conn.length_limit / x) + 1

        import random
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
                self.notice_window.bkgd(" ", curses.color_pair(colour_fields["timelines"]))

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

        self.status_window.bkgd(" ", curses.color_pair(colour_fields["statusbar"]))
        self.tab_bar_window.bkgd(" ", curses.color_pair(colour_fields["tabbar"]))

    def initialise(self, screen):
        self.screen = screen

        curses.noecho()
        curses.cbreak()
        curses.use_default_colors()

        if curses.has_colors() and config.config['enable_colours'] == True:
            curses.start_color()

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
            tab = tabspec.split(':')
            if tab[0] in ("home", "mentions", "direct", "public", "sentdirect"):
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
                self.tabs.append(Context(self.conn, self.notice_window, notice_id))
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
        running = True

        while running:
            input = self.main_window.getch()
           
            if self.qreply == False:
                switch_to_tab = None
                for x in range(0, len(self.tabs)):
                    if x >= 9:
                        break
                    if input == ord(str(x+1)):
                        switch_to_tab = x
                if input == ord(">") or input in [ord(key) for key in config.config['keys']['nexttab']]:
                    if self.current_tab < (len(self.tabs) - 1):
                        switch_to_tab = self.current_tab + 1
                elif input == ord("<") or input in [ord(key) for key in config.config['keys']['prevtab']]:
                    if self.current_tab >= 1:
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
            
            if input == curses.KEY_UP or input in [ord(key) for key in config.config['keys']['scrollup']]:
                self.tabs[self.current_tab].scrollup(1)
                self.display_current_tab()
            elif input == curses.KEY_HOME or input in [ord(key) for key in config.config['keys']['scrolltop']]:
                self.tabs[self.current_tab].scrollup(0)
                self.display_current_tab()
            elif input == curses.KEY_PPAGE or input in [ord(key) for key in config.config['keys']['pageup']]:
                self.tabs[self.current_tab].scrollup(self.main_window.getmaxyx()[0] - 11) # the 11 offset gives 2 lines of overlap between the pre-scroll view and post-scroll view
                self.display_current_tab()
            elif input == curses.KEY_DOWN or input in [ord(key) for key in config.config['keys']['scrolldown']]:
                self.tabs[self.current_tab].scrolldown(1)
                self.display_current_tab()
            elif input == curses.KEY_END or input in [ord(key) for key in config.config['keys']['scrollbottom']]:
                self.tabs[self.current_tab].scrolldown(0)
                self.display_current_tab()
            elif input == curses.KEY_NPAGE or input in [ord(key) for key in config.config['keys']['pagedown']]:
                self.tabs[self.current_tab].scrolldown(self.main_window.getmaxyx()[0] - 11) # as above
                self.display_current_tab()
            elif input == ord("=") or input in [ord(key) for key in config.config['keys']['firstpage']]:
                if self.tabs[self.current_tab].prevpage(0):
                    self.status_bar.update("Moving to first page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input == curses.KEY_LEFT or input in [ord(key) for key in config.config['keys']['newerpage']]:
                if self.tabs[self.current_tab].prevpage():
                    self.status_bar.update("Moving to newer page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input == curses.KEY_RIGHT or input in [ord(key) for key in config.config['keys']['olderpage']]:
                if self.tabs[self.current_tab].nextpage():
                    self.status_bar.update("Moving to older page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update("Doing nothing.")
            elif input == ord("r") or input in [ord(key) for key in config.config['keys']['refresh']]:
                self.update_tabs()
            elif input == ord("i") or input in [ord(key) for key in config.config['keys']['input']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit())
            elif input == ord(":") or input in [ord(key) for key in config.config['keys']['commandinput']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit("/"))
            elif input == ord("/") or input in [ord(key) for key in config.config['keys']['search']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.search_mode = True
                self.parse_search(self.text_entry.edit())
            elif input == ord("q") or input in [ord(key) for key in config.config['keys']['quit']]:
                running = False
            elif input == ord("x") or input in [ord(key) for key in config.config['keys']['closetab']]:
                self.close_current_tab()
            elif input == ord("h") or input in [ord(key) for key in config.config['keys']['help']]:
                self.tabs.append(Help(self.notice_window, self.path))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
            elif input == ord("l") or input in [ord(key) for key in config.config['keys']['qreply']]:
                self.qreply = True
            elif input == ord("d") or input in [ord(key) for key in config.config['keys']['creply']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit("/r " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
            elif input == ord("s") or input in [ord(key) for key in config.config['keys']['cnext']]:
                if self.tabs[self.current_tab].chosen_one != (len(self.tabs[self.current_tab].timeline) - 1):
                    self.tabs[self.current_tab].chosen_one += 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one, smooth_scroll=config.config["smooth_cscroll"])
            elif input == ord("a") or input in [ord(key) for key in config.config['keys']['cprev']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one -= 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one, smooth_scroll=config.config["smooth_cscroll"])
            elif input == ord("z") or input in [ord(key) for key in config.config['keys']['cfirst']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one = 0
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("f") or input in [ord(key) for key in config.config['keys']['cfav']]:
                self.status_bar.update("Favouriting Notice...")
                if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                else:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                try:
                    self.conn.favorites_create(id)
                except StatusNetError, e:
                    self.status_bar.timed_update("Status.Net error %d: %s" % (e.errcode, e.details))
                self.status_bar.update("Doing Nothing.")
            elif input == ord("e") or input in [ord(key) for key in config.config['keys']['crepeat']]:
                try:
                    self.status_bar.update("Repeating Notice...")
                    if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                        id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                    else:
                        id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                except IndexError, e:  # shit broke, debug time
                    debug_filename = os.path.join(os.path.expanduser("~"), "identicurse_debug.txt")
                    open(debug_filename, "w").write("IndexError\n%s\n\tself.current_tab = %d ; len(self.tabs) = %d ; chosen_one = %d ; len(self.tabs[self.current_tab].timeline) = %d\n"
                            % (str(e), self.current_tab, len(self.tabs), self.tabs[self.current_tab].chosen_one, len(self.tabs[self.current_tab].timeline)))
                    self.status_bar.update("Something broke, please get a copy of '%s' to @psquid." % (debug_filename))
                try:
                    update = self.conn.statuses_retweet(id, source="IdentiCurse")
                    if isinstance(update, list):
                        for notice in update:
                            self.tabs[self.current_tab].timeline.insert(0, notice)
                    else:
                        self.tabs[self.current_tab].timeline.insert(0, update)
                    self.tabs[self.current_tab].update_buffer()
                except StatusNetError, e:
                    self.status_bar.timed_update("Status.Net error %d: %s" % (e.errcode, e.details))
                self.status_bar.update("Doing Nothing.")
            elif input == ord("c") or input in [ord(key) for key in config.config['keys']['ccontext']]:
                self.status_bar.update("Loading Context...")
                if "retweeted_status" in self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['retweeted_status']['id']
                else:
                    id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                self.tabs.append(Context(self.conn, self.notice_window, id))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
                self.status_bar.update("Doing Nothing.")
            elif input == ord("n") or input in [ord(key) for key in config.config['keys']['nextmatch']]:
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
            elif input == ord("N") or input in [ord(key) for key in config.config['keys']['prevmatch']]:
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
            elif input == curses.ascii.ctrl(ord("l")):
                self.redraw()

            y, x = self.screen.getmaxyx()
            if y != self.y or x != self.x:
                self.redraw()
                self.update_tab_buffers()


            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, character_count):
        if self.quote_mode:
            if self.conn.length_limit == 0:
                self.status_bar.update("Quote Mode: " + str(character_count))
            else:
                self.status_bar.update("Quote Mode: " + str(self.conn.length_limit - character_count))
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

        if input is None:
            input = ""

        if len(input) > 0:      # don't do anything if the user didn't enter anything
            input = input.rstrip()

            tokens = [token for token in input.split(" ") if token != ""]

            if tokens[0][0] == "i" and ((tokens[0][1:] in self.known_commands) or (tokens[0][1:] in config.config["aliases"])):
                tokens[0] = tokens[0][1:]  # avoid doing the wrong thing when people accidentally submit stuff like "i/r 2 blabla"

            # catch mistakes like "/r1" - the last condition is so that, for example, "/directs" is not mistakenly converted to "/direct s"
            for command in self.known_commands:
                if (tokens[0][:len(command)] == command) and (tokens[0] != command) and not (tokens[0] in self.known_commands) and not (tokens[0] in config.config['aliases']):
                    tokens[:1] = [command, tokens[0].replace(command, "")]
            for alias in config.config['aliases']:
                if (tokens[0][:len(alias)] == alias) and (tokens[0] != alias) and not (tokens[0] in self.known_commands) and not (tokens[0] in config.config['aliases']):
                    tokens[:1] = [alias, tokens[0].replace(alias, "")]

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
                    if tokens[0] == "/reply" and len(tokens) >= 3:
                        self.status_bar.update("Posting Reply...")
    
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = 0  # this is not a reply to a dent
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        status = "@" + user + " " + " ".join(tokens[2:])
    
                        try:
                            update = self.conn.statuses_update(status, "IdentiCurse", int(id), long_dent=config.config['long_dent'], dup_first_word=True)
                        except Exception, (errmsg):
                            self.status_bar.timed_update("ERROR: Couldn't post status: %s" % (errmsg))
    
                    elif tokens[0] == "/favourite" and len(tokens) == 2:
                        self.status_bar.update("Favouriting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        self.conn.favorites_create(id)
    
                    elif tokens[0] == "/repeat" and len(tokens) == 2:
                        self.status_bar.update("Repeating Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        update = self.conn.statuses_retweet(id, source="IdentiCurse")
                        
                    elif tokens[0] == "/direct" and len(tokens) >= 3:
                        self.status_bar.update("Sending Direct...")
                        
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
                        id = self.conn.users_show(screen_name=screen_name)['id']
                        
                        self.conn.direct_messages_new(screen_name, id, " ".join(tokens[2:]), source="IdentiCurse")
    
                    elif tokens[0] == "/delete" and len(tokens) == 2:
                        self.status_bar.update("Deleting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            repeat_id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        try:
                            self.conn.statuses_destroy(id)
                        except statusnet.StatusNetError, e:
                            if e.errcode == 403:  # user doesn't own the original status, so is probably trying to delete the repeat
                                self.conn.statuses_destroy(repeat_id)
                            else:  # it wasn't a 403, so re-raise
                                raise(e)
    
                    elif tokens[0] == "/profile" and len(tokens) == 2:
                        self.status_bar.update("Loading Profile...")
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
    
                        self.tabs.append(Profile(self.conn, self.notice_window,user))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/spamreport" and len(tokens) >= 3:
                        self.status_bar.update("Firing Orbital Laser Cannon...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            username = tokens[1]
                            if username[0] == "@":
                                    username = username[1:]
                            id = self.conn.users_show(screen_name=username)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['user']['id']
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["user"]["screen_name"]
                            else:
                                id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                                username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        status = "@support !sr @%s UID %d %s" % (username, id, " ".join(tokens[2:]))
                        update = self.conn.statuses_update(status, "IdentiCurse")
                        self.conn.blocks_create(user_id=id, screen_name=username)
    
                    elif tokens[0] == "/block" and len(tokens) >= 2:
                        self.status_bar.update("Creating Block(s)...")
                        for token in tokens[1:]:
                            # Yeuch
                            try:
                                float(token)
                            except ValueError:
                                user = token
                                if user[0] == "@":
                                    user = user[1:]
                                id = self.conn.users_show(screen_name=user)['id']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                            self.conn.blocks_create(user_id=id, screen_name=user)
    
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
                                id = self.conn.users_show(screen_name=user)['id']
                            else:
                                if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                                else:
                                    user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                    id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                            self.conn.blocks_destroy(user_id=id, screen_name=user)
    
                    elif tokens[0] == "/user" and len(tokens) == 2:
                        self.status_bar.update("Loading User Timeline...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                        
                        self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'user_id':id, 'screen_name':user}))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/context" and len(tokens) == 2:
                        self.status_bar.update("Loading Context...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["retweeted_status"]["id"]
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]
    
                        self.tabs.append(Context(self.conn, self.notice_window, id))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/subscribe" and len(tokens) == 2:
                        self.status_bar.update("Subscribing...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
    
                        self.conn.friendships_create(user_id=id, screen_name=user)
                        
                    elif tokens[0] == "/unsubscribe" and len(tokens) == 2:
                        self.status_bar.update("Unsubscribing...")
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                                    user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["retweeted_status"]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['retweeted_status']['user']['id']
                            else:
                                user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                                id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
    
                        self.conn.friendships_destroy(user_id=id, screen_name=user)
    
                    elif tokens[0] == "/group" and len(tokens) == 2:
                        self.status_bar.update("Loading Group Timeline...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'group_id':id, 'nickname':group}))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/groupjoin" and len(tokens) == 2:
                        self.status_bar.update("Joining Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_join(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupleave" and len(tokens) == 2:
                        self.status_bar.update("Leaving Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_leave(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupmember" and len(tokens) == 2:
                        self.status_bar.update("Checking membership...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
                        user_id = int(self.conn.users_show(screen_name=config.config['username'])['id'])

                        if self.conn.statusnet_groups_is_member(user_id, group_id):
                            self.status_bar.timed_update("You are a member of !%s." % (group))
                        else:
                            self.status_bar.timed_update("You are not a member of !%s." % (group))

                    elif tokens[0] == "/tag" and len(tokens) == 2:
                        self.status_bar.update("Loading Tag Timeline...")
                        tag = tokens[1]
                        if tag[0] == "#":
                            tag = tag[1:]
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/sentdirects" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "sentdirect":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.status_bar.update("Loading Sent Directs...")
                            self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/favourites" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "favourites":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.status_bar.update("Loading Favourites...")
                            self.tabs.append(Timeline(self.conn, self.notice_window, "favourites"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/search" and len(tokens) >= 2:
                        self.status_bar.update("Searching...")
                        query = " ".join(tokens[1:])
                        self.tabs.append(Timeline(self.conn, self.notice_window, "search"))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/home" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "home":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.tabs.append(Timeline(self.conn, self.notice_window, "home"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/mentions" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "mentions":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.tabs.append(Timeline(self.conn, self.notice_window, "mentions"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/directs" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "direct":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.tabs.append(Timeline(self.conn, self.notice_window, "direct"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/public" and len(tokens) == 1:
                        already_have_one = False
                        for tab in self.tabs:
                            if hasattr(tab, 'timeline_type'):
                                if tab.timeline_type == "public":
                                    already_have_one = True
                                    break
                        if not already_have_one:
                            self.tabs.append(Timeline(self.conn, self.notice_window, "public"))
                            self.tabs[self.current_tab].active = False
                            self.current_tab = len(self.tabs) - 1
                            self.tabs[self.current_tab].active = True
                            self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/config" and len(tokens) >= 3:
                        keys, value = tokens[1].split('.'), " ".join(tokens[2:])
                        if len(keys) == 2:      # there has to be a clean way to avoid hardcoded len checks, but I can't think what right now, and technically it works for all currently valid config keys
                            config.config[keys[0]][keys[1]] = value
                        else:
                            config.config[keys[0]] = value
                        config.config.save()
    
                    elif tokens[0] == "/alias" and len(tokens) >= 3:
                        self.status_bar.update("Creating alias...")
                        alias, command = tokens[1], " ".join(tokens[2:])
                        if alias[0] != "/":
                            alias = "/" + alias
                        if command[0] != "/":
                            command = "/" + command
                        config.config["aliases"][alias] = command
                        config.config.save()

                    elif tokens[0] == "/link":
                        dent_index = int(tokens[2]) - 1
                        if tokens[1] == "*":
                            self.status_bar.update("Opening links...")
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text']):
                                    subprocess.Popen(config.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                            else:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text']):
                                    subprocess.Popen(config.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                        else:
                            self.status_bar.update("Opening link...")
                            link_index = int(tokens[1]) - 1
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text'])[link_index]
                            else:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text'])[link_index]
                            subprocess.Popen(config.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

                    elif tokens[0] == "/bugreport" and len(tokens) >= 2:
                        self.status_bar.update("Reporting bug...")
    
                        status = "#icursebug " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=config.config['long_dent'], dup_first_word=True)
   
                    elif tokens[0] == "/featurerequest" and len(tokens) >= 2:
                        self.status_bar.update("Posting feature request...")
    
                        status = "#icurserequest " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=config.config['long_dent'], dup_first_word=True)

                    elif tokens[0] == "/quote" and len(tokens) == 2:
                        self.quote_mode = True

                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            original_id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            original_id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        original_status = self.conn.statuses_show(original_id)
                        new_status_base = "RD @%s %s" % (original_status['user']['screen_name'], original_status['text'])

                        status = self.text_entry.edit(new_status_base)
                        self.quote_mode = False

                        if status is None:
                            status = ""
                        if len(status) > 0:
                            self.status_bar.update("Posting Notice...")
                            update = self.conn.statuses_update(status, "IdentiCurse", original_id, long_dent=config.config['long_dent'])
   
                except StatusNetError, e:
                    self.status_bar.timed_update("Status.Net error %d: %s" % (e.errcode, e.details))
            else:
                self.status_bar.update("Posting Notice...")
                try:
                    update = self.conn.statuses_update(input, source="IdentiCurse", long_dent=config.config['long_dent'])
                except Exception, (errmsg):
                    self.status_bar.timed_update("ERROR: Couldn't post status: %s" % (errmsg))

        if hasattr(self.tabs[self.current_tab], 'timeline_type'):
            if update != False:
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
            else:
                self.tabs[self.current_tab].update()
        elif update != False and self.tabs[self.current_tab].name == "Context":
            self.tabs[self.current_tab].timeline.insert(0, update)
            self.tabs[self.current_tab].update_buffer()
            self.status_bar.update("Doing nothing.")
        else:
            self.tabs[self.current_tab].update()
          

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.tabs[self.current_tab].search_highlight_line = -1
        self.display_current_tab()
        self.status_bar.update("Doing nothing.")
        self.insert_mode = False
        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

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

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.display_current_tab()
        self.insert_mode = False
        self.search_mode = False
        self.update_timer = Timer(config.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def quit(self):
        self.update_timer.cancel()
        curses.endwin()
        sys.exit()
