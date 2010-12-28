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

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self):
        self.path = os.path.dirname(os.path.realpath( __file__ ))
        self.qreply = False
        
        self.config_file = os.path.join(os.path.expanduser("~") ,".identicurse")
        try:
            if os.path.exists(self.config_file):
                self.config = json.loads(open(self.config_file).read())
            else:
                self.config_file = os.path.join(self.path, "config.json")
                self.config = json.loads(open(self.config_file).read())
        except:
            sys.exit("ERROR: Couldn't read config file.")

        self.last_page_search = {'query':"", 'occurs':[], 'viewing':0}

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
            "/link",
            "/bugreport",
            "/featurerequest"
            ]

        # set some defaults for configs that we will always need to use, but that are optional
        if not "search_case_sensitive" in self.config:
            self.config['search_case_sensitive'] = "sensitive"
        if not "long_dent" in self.config:
            self.config['long_dent'] = "split"
        if not "filters" in self.config:
            self.config['filters'] = []
        if not "notice_limit" in self.config:
            self.config['notice_limit'] = 25
        if not "browser" in self.config:
            self.config['browser'] = "xdg-open '%s'"

        if not "keys" in self.config:
            self.config['keys'] = {}
        if not "scrollup" in self.config['keys']:
            self.config['keys']['scrollup'] = ['k']
        if not "scrolltop" in self.config['keys']:
            self.config['keys']['scrolltop'] = ['g']
        if not "pageup" in self.config['keys']:
            self.config['keys']['pageup'] = ['b']
        if not "scrolldown" in self.config['keys']:
            self.config['keys']['scrolldown'] = ['j']
        if not "scrollbottom" in self.config['keys']:
            self.config['keys']['scrollbottom'] = ['G']
        if not "pagedown" in self.config['keys']:
            self.config['keys']['pagedown'] = [' ']
        if not "firstpage" in self.config['keys']:
            self.config['keys']['firstpage'] = []
        if not "newerpage" in self.config['keys']:
            self.config['keys']['newerpage'] = []
        if not "olderpage" in self.config['keys']:
            self.config['keys']['olderpage'] = []
        if not "refresh" in self.config['keys']:
            self.config['keys']['refresh'] = []
        if not "input" in self.config['keys']:
            self.config['keys']['input'] = []
        if not "search" in self.config['keys']:
            self.config['keys']['search'] = []
        if not "quit" in self.config['keys']:
            self.config['keys']['quit'] = []
        if not "closetab" in self.config['keys']:
            self.config['keys']['closetab'] = []
        if not "help" in self.config['keys']:
            self.config['keys']['help'] = []
        if not "nexttab" in self.config['keys']:
            self.config['keys']['nexttab'] = []
        if not "prevtab" in self.config['keys']:
            self.config['keys']['prevtab'] = []
        if not "qreply" in self.config['keys']:
            self.config['keys']['qreply'] = []
        if not "creply" in self.config['keys']:
            self.config['keys']['creply'] = []
        if not "cfav" in self.config['keys']:
            self.config['keys']['cfav'] = []
        if not "ccontext" in self.config['keys']:
            self.config['keys']['ccontext'] = []
        if not "crepeat" in self.config['keys']:
            self.config['keys']['crepeat'] = []
        if not "cnext" in self.config['keys']:
            self.config['keys']['cnext'] = []
        if not "cprev" in self.config['keys']:
            self.config['keys']['cprev'] = []
        if not "cfirst" in self.config['keys']:
            self.config['keys']['cfirst'] = []

        self.url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

        try:
            self.conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])
        except Exception, (errmsg):
            sys.exit("ERROR: Couldn't establish connection: %s" % (errmsg))

        self.insert_mode = False
        curses.wrapper(self.initialise)

    def redraw(self):
        self.screen.erase()
        self.y, self.x = self.screen.getmaxyx()

        self.main_window = self.screen.subwin(self.y-2, self.x-3, 2, 2)
        self.main_window.keypad(1)
        self.main_window.box(0, 0)

        y, x = self.main_window.getmaxyx()

        if self.conn.length_limit == 0:
            entry_lines = 3
        else:
            entry_lines = (self.conn.length_limit / x) + 1

        self.entry_window = self.main_window.subwin(entry_lines, x-10, 4, 5)

        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)

        self.text_entry.stripspaces = 1
        self.notice_window = self.main_window.subwin(y-7, x-4, 5 + entry_lines, 5)

        # I don't like this, but it looks like it has to be done
        if hasattr(self, 'tabs'):
            for tab in self.tabs:
                tab.window = self.notice_window

        self.status_window = self.main_window.subwin(1, x-4, y, 5)
        if hasattr(self, 'status_bar'):
            self.status_bar.window = self.status_window

    def initialise(self, screen):
        self.screen = screen

        curses.noecho()
        curses.cbreak()
        curses.use_default_colors()

        self.redraw()

        self.status_bar = StatusBar(self.status_window)
        self.status_bar.update_left("Welcome to IdentiCurse")
        
        self.tabs = []
        for tabspec in self.config['initial_tabs'].split("|"):
            tab = tabspec.split(':')
            if tab[0] == "home":
                self.tabs.append(Timeline(self.conn, self.notice_window, "home", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "mentions":
                self.tabs.append(Timeline(self.conn, self.notice_window, "mentions", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "direct":
                self.tabs.append(Timeline(self.conn, self.notice_window, "direct", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "public":
                self.tabs.append(Timeline(self.conn, self.notice_window, "public", filters=self.config['filters']))
            if tab[0] == "profile":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                self.tabs.append(Profile(self.conn, self.notice_window, screen_name))
            if tab[0] == "sentdirect":
                self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "user":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                user_id = self.conn.users_show(screen_name=screen_name)['id']
                self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'screen_name':screen_name, 'user_id':user_id}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "group":
                nickname = tab[1]
                if nickname[0] == "!":
                    nickname = nickname[1:]
                group_id = int(self.conn.statusnet_groups_show(nickname=nickname)['id'])
                self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'nickname':nickname, 'group_id':group_id}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "tag":
                tag = tab[1]
                if tag[0] == "#":
                    tag = tag[1:]
                self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
            if tab[0] == "search":
                self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':tab[1]}, filters=self.config['filters']))
            #not too sure why anyone would need to auto-open these last two, but it couldn't hurt to add them
            if tab[0] == "context":
                notice_id = int(tab[1])
                self.tabs.append(Context(self.conn, self.notice_window, notice_id))
            if tab[0] == "help":
                self.tabs.append(Help(self.notice_window, self.path))

        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

        self.current_tab = 0
        self.tabs[self.current_tab].active = True
        self.tab_order = range(len(self.tabs))

        self.update_tabs()
        self.display_current_tab()

        self.loop()

    def update_tabs(self):
        self.update_timer.cancel()
        if self.insert_mode == False:
            self.status_bar.update_left("Updating Timelines...")
            TabUpdater(self.tabs, self, 'end_update_tabs').start()
        else:
            self.update_timer = Timer(self.config['update_interval'], self.update_tabs)

    def end_update_tabs(self):
        self.display_current_tab()
        self.status_bar.update_left("Doing nothing.")
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def update_tab_buffers(self):
        for tab in self.tabs:
            tab.update_buffer()

    def display_current_tab(self):
        self.tabs[self.current_tab].display()
        self.status_bar.update_right("Tab " + str(self.current_tab + 1) + ": " + self.tabs[self.current_tab].name)

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
                    if input == ord(str(x+1)):
                        switch_to_tab = x
                if input == ord("n") or input in [ord(key) for key in self.config['keys']['nexttab']]:
                    if self.current_tab < (len(self.tabs) - 1):
                        switch_to_tab = self.current_tab + 1
                elif input == ord("p") or input in [ord(key) for key in self.config['keys']['prevtab']]:
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
            
            if input == curses.KEY_UP or input in [ord(key) for key in self.config['keys']['scrollup']]:
                self.tabs[self.current_tab].scrollup(1)
                self.display_current_tab()
            elif input == curses.KEY_HOME or input in [ord(key) for key in self.config['keys']['scrolltop']]:
                self.tabs[self.current_tab].scrollup(0)
                self.display_current_tab()
            elif input == curses.KEY_PPAGE or input in [ord(key) for key in self.config['keys']['pageup']]:
                self.tabs[self.current_tab].scrollup(self.main_window.getmaxyx()[0] - 11) # the 11 offset gives 2 lines of overlap between the pre-scroll view and post-scroll view
                self.display_current_tab()
            elif input == curses.KEY_DOWN or input in [ord(key) for key in self.config['keys']['scrolldown']]:
                self.tabs[self.current_tab].scrolldown(1)
                self.display_current_tab()
            elif input == curses.KEY_END or input in [ord(key) for key in self.config['keys']['scrollbottom']]:
                self.tabs[self.current_tab].scrolldown(0)
                self.display_current_tab()
            elif input == curses.KEY_NPAGE or input in [ord(key) for key in self.config['keys']['pagedown']]:
                self.tabs[self.current_tab].scrolldown(self.main_window.getmaxyx()[0] - 11) # as above
                self.display_current_tab()
            elif input == ord("=") or input in [ord(key) for key in self.config['keys']['firstpage']]:
                if self.tabs[self.current_tab].prevpage(0):
                    self.status_bar.update_left("Moving to first page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == curses.KEY_LEFT or input in [ord(key) for key in self.config['keys']['newerpage']]:
                if self.tabs[self.current_tab].prevpage():
                    self.status_bar.update_left("Moving to newer page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == curses.KEY_RIGHT or input in [ord(key) for key in self.config['keys']['olderpage']]:
                if self.tabs[self.current_tab].nextpage():
                    self.status_bar.update_left("Moving to older page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == ord("r") or input in [ord(key) for key in self.config['keys']['refresh']]:
                self.update_tabs()
            elif input == ord("i") or input in [ord(key) for key in self.config['keys']['input']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.status_bar.update_left("Insert Mode: 0")
                self.parse_input(self.text_entry.edit())
            elif input == ord("/") or input in [ord(key) for key in self.config['keys']['search']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_search(self.text_entry.edit())
            elif input == ord("q") or input in [ord(key) for key in self.config['keys']['quit']]:
                running = False
            elif input == ord("x") or input in [ord(key) for key in self.config['keys']['closetab']]:
                self.close_current_tab()
            elif input == ord("h") or input in [ord(key) for key in self.config['keys']['help']]:
                self.tabs.append(Help(self.notice_window, self.path))
                self.tabs[self.current_tab].active = False
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].active = True
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
            elif input == ord("l") or input in [ord(key) for key in self.config['keys']['qreply']]:
                self.qreply = True
            elif input == ord("d") or input in [ord(key) for key in self.config['keys']['creply']]:
                self.update_timer.cancel()
                self.insert_mode = True
                self.parse_input(self.text_entry.edit("/r " + str(self.tabs[self.current_tab].chosen_one + 1) + " "))
            elif input == ord("s") or input in [ord(key) for key in self.config['keys']['cnext']]:
                if self.tabs[self.current_tab].chosen_one != (len(self.tabs[self.current_tab].timeline) - 1):
                    self.tabs[self.current_tab].chosen_one += 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("a") or input in [ord(key) for key in self.config['keys']['cprev']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one -= 1
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("z") or input in [ord(key) for key in self.config['keys']['cfirst']]:
                if self.tabs[self.current_tab].chosen_one != 0:
                    self.tabs[self.current_tab].chosen_one = 0
                    self.tabs[self.current_tab].update_buffer()
                    self.tabs[self.current_tab].scrolltodent(self.tabs[self.current_tab].chosen_one)
            elif input == ord("f") or input in [ord(key) for key in self.config['keys']['cfav']]:
                self.status_bar.update_left("Favouriting Notice...")
                id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                self.conn.favorites_create(id)
                self.status_bar.update_left("Doing Nothing.")
            elif input == ord("e") or input in [ord(key) for key in self.config['keys']['crepeat']]:
                self.status_bar.update_left("Repeating Notice...")
                id = self.tabs[self.current_tab].timeline[self.tabs[self.current_tab].chosen_one]['id']
                update = self.conn.statuses_retweet(id, source="IdentiCurse")
                if isinstance(update, list):
                    for notice in update:
                        self.tabs[self.current_tab].timeline.insert(0, notice)
                else:
                    self.tabs[self.current_tab].timeline.insert(0, update)
                self.tabs[self.current_tab].update_buffer()
                self.status_bar.update_left("Doing Nothing.")
            elif input == ord("c") or input in [ord(key) for key in self.config['keys']['ccontext']]:
                self.status_bar.update_left("Loading Context...")
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
                self.status_bar.update_left("Doing Nothing.")

            y, x = self.screen.getmaxyx()
            if y != self.y or x != self.x:
                self.redraw()
                self.update_tab_buffers()

            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, character_count):
        self.status_bar.update_left("Insert Mode: " + str(character_count))

    def parse_input(self, input):
        update = False

        if input is None:
            input = ""

        if len(input) > 0:      # don't do anything if the user didn't enter anything
            input = input.rstrip()

            tokens = [token for token in input.split(" ") if token != ""]

            if tokens[0][0] == "i" and ((tokens[0][1:] in self.known_commands) or (tokens[0][1:] in self.config["aliases"])):
                tokens[0] = tokens[0][1:]  # avoid doing the wrong thing when people accidentally submit stuff like "i/r 2 blabla"

            if tokens[0] in self.config["aliases"]:
                tokens = self.config["aliases"][tokens[0]].split(" ") + tokens[1:]

            try:
                if ("direct" in self.tabs[self.current_tab].timeline_type) and (tokens[0] == "/reply"):
                    tokens[0] = "/direct"
            except AttributeError:
                # the tab has no timeline_type, so it's *definitely* not directs.
                pass

            if tokens[0] in self.known_commands:
                
                try:
                    if tokens[0] == "/reply" and len(tokens) >= 3:
                        self.status_bar.update_left("Posting Reply...")
    
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
                            update = self.conn.statuses_update(status, "IdentiCurse", int(id), long_dent=self.config['long_dent'])
                        except Exception, (errmsg):
                            self.status_bar.timed_update_left("ERROR: Couldn't post status: %s" % (errmsg))
    
                    elif tokens[0] == "/favourite" and len(tokens) == 2:
                        self.status_bar.update_left("Favouriting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        self.conn.favorites_create(id)
    
                    elif tokens[0] == "/repeat" and len(tokens) == 2:
                        self.status_bar.update_left("Repeating Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        update = self.conn.statuses_retweet(id, source="IdentiCurse")
                        
                    elif tokens[0] == "/direct" and len(tokens) >= 3:
                        self.status_bar.update_left("Sending Direct...")
                        
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
                        self.status_bar.update_left("Deleting Notice...")
                        if "retweeted_status" in self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['retweeted_status']['id']
                        else:
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                        try:
                            self.conn.statuses_destroy(id)
                        except urllib2.HTTPError, e:
                            if e.code == 403:
                                self.status_bar.timed_update_left("ERROR: You cannot delete others' statuses.")
    
                    elif tokens[0] == "/profile" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Profile...")
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
                        self.status_bar.update_left("Firing Orbital Laser Cannon...")
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
                        self.status_bar.update_left("Creating Block(s)...")
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
                        self.status_bar.update_left("Removing Block(s)...")
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
                        self.status_bar.update_left("Loading User Timeline...")
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
                        
                        self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'user_id':id, 'screen_name':user}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/context" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Context...")
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
                        self.status_bar.update_left("Subscribing...")
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
                        self.status_bar.update_left("Unsubscribing...")
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
                        self.status_bar.update_left("Loading Group Timeline...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'group_id':id, 'nickname':group}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/groupjoin" and len(tokens) == 2:
                        self.status_bar.update_left("Joining Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_join(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupleave" and len(tokens) == 2:
                        self.status_bar.update_left("Leaving Group...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
    
                        self.conn.statusnet_groups_leave(group_id=id, nickname=group)
    
                    elif tokens[0] == "/groupmember" and len(tokens) == 2:
                        self.status_bar.update_left("Checking membership...")
                        group = tokens[1]
                        if group[0] == "!":
                            group = group[1:]
                        group_id = int(self.conn.statusnet_groups_show(nickname=group)['id'])
                        user_id = int(self.conn.users_show(screen_name=self.config['username'])['id'])

                        if self.conn.statusnet_groups_is_member(user_id, group_id):
                            self.status_bar.timed_update_left("You are a member of !%s." % (group))
                        else:
                            self.status_bar.timed_update_left("You are not a member of !%s." % (group))

                    elif tokens[0] == "/tag" and len(tokens) == 2:
                        self.status_bar.update_left("Loading Tag Timeline...")
                        tag = tokens[1]
                        if tag[0] == "#":
                            tag = tag[1:]
    
                        self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}, notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/sentdirects" and len(tokens) == 1:
                        self.status_bar.update_left("Loading Sent Directs...")
                        self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
    
                    elif tokens[0] == "/favourites" and len(tokens) == 1:
                        self.status_bar.update_left("Loading Favourites...")
                        self.tabs.append(Timeline(self.conn, self.notice_window, "favourites", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/search" and len(tokens) >= 2:
                        self.status_bar.update_left("Searching...")
                        query = " ".join(tokens[1:])
                        self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':query}, filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/home" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "home", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/mentions" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "mentions", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/directs" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "direct", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                    
                    elif tokens[0] == "/public" and len(tokens) == 1:
                        self.tabs.append(Timeline(self.conn, self.notice_window, "public", notice_limit=self.config['notice_limit'], filters=self.config['filters']))
                        self.tabs[self.current_tab].active = False
                        self.current_tab = len(self.tabs) - 1
                        self.tabs[self.current_tab].active = True
                        self.tab_order.insert(0, self.current_tab)
                        
                    elif tokens[0] == "/config" and len(tokens) >= 3:
                        keys, value = tokens[1].split('.'), " ".join(tokens[2:])
                        if len(keys) == 2:      # there has to be a clean way to avoid hardcoded len checks, but I can't think what right now, and technically it works for all currently valid config keys
                            self.config[keys[0]][keys[1]] = value
                        else:
                            self.config[keys[0]] = value
                        open(self.config_file, 'w').write(json.dumps(self.config, indent=4))
    
                    elif tokens[0] == "/link":
                        dent_index = int(tokens[2]) - 1
                        if tokens[1] == "*":
                            self.status_bar.update_left("Opening links...")
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text']):
                                    subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                            else:
                                for target_url in self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text']):
                                    subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                        else:
                            self.status_bar.update_left("Opening link...")
                            link_index = int(tokens[1]) - 1
                            if "retweeted_status" in self.tabs[self.current_tab].timeline[dent_index]:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['retweeted_status']['text'])[link_index]
                            else:
                                target_url = self.url_regex.findall(self.tabs[self.current_tab].timeline[dent_index]['text'])[link_index]
                            subprocess.Popen(self.config['browser'] % (target_url), shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

                    elif tokens[0] == "/bugreport" and len(tokens) >= 2:
                        self.status_bar.update_left("Reporting bug...")
    
                        status = "#icursebug " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=self.config['long_dent'], dup_first_word=True)
   
                    elif tokens[0] == "/featurerequest" and len(tokens) >= 2:
                        self.status_bar.update_left("Posting feature request...")
    
                        status = "#icurserequest " + " ".join(tokens[1:])
                        update = self.conn.statuses_update(status, "IdentiCurse", long_dent=self.config['long_dent'], dup_first_word=True)
   
                except StatusNetError, e:
                    self.status_bar.timed_update_left("Status.Net error %d: %s" % (e.errcode, e.details))
            else:
                self.status_bar.update_left("Posting Notice...")
                try:
                    update = self.conn.statuses_update(input, source="IdentiCurse", long_dent=self.config['long_dent'])
                except Exception, (errmsg):
                    self.status_bar.timed_update_left("ERROR: Couldn't post status: %s" % (errmsg))

        if hasattr(self.tabs[self.current_tab], 'timeline_type'):
            if update != False and (self.tabs[self.current_tab].timeline_type == 'home' or self.tabs[self.current_tab].timeline_type == 'mentions'):
                if isinstance(update, list):
                    for notice in update:
                        self.tabs[self.current_tab].timeline.insert(0, notice)
                else:
                    self.tabs[self.current_tab].timeline.insert(0, update)
                self.tabs[self.current_tab].update_buffer()
                self.status_bar.update_left("Doing nothing.")
            else:
                self.tabs[self.current_tab].update()
        elif update != False and self.tabs[self.current_tab].name == "Context":
            self.tabs[self.current_tab].timeline.insert(0, update)
            self.tabs[self.current_tab].update_buffer()
            self.status_bar.update_left("Doing nothing.")
        else:
            self.tabs[self.current_tab].update()
          

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.display_current_tab()
        self.status_bar.update_left("Doing nothing.")
        self.insert_mode = False
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def parse_search(self, query):
        if query is not None:
            query = query.rstrip()
            if query == "":
                query = self.last_page_search['query']
            if (self.last_page_search['query'] == query) and not (query == ""):
                # this is a continued search
                if self.last_page_search['viewing'] < (len(self.last_page_search['occurs']) - 1):
                    self.last_page_search['viewing'] += 1
                    self.tabs[self.current_tab].scrollto(self.last_page_search['occurs'][self.last_page_search['viewing']])
                    self.status_bar.update_left("Viewing result #%d for '%s'" % (self.last_page_search['viewing'] + 1, query))
                    self.display_current_tab()
                else:
                    self.status_bar.update_left("No more results for '%s'" % (query))
            else:
                # new search
                maxx = self.tabs[self.current_tab].window.getmaxyx()[1]
                search_buffer = self.tabs[self.current_tab].buffer.reflowed(maxx - 2)

                page_search = {'query':query, 'occurs':[], 'viewing':0}
                
                for line_index in range(len(search_buffer)):
                    if self.config['search_case_sensitive'] == "sensitive":
                        if query in search_buffer[line_index]:
                            page_search['occurs'].append(line_index)
                    else:
                        if query.upper() in search_buffer[line_index].upper():
                            page_search['occurs'].append(line_index)

                if len(page_search['occurs']) > 0:
                    self.tabs[self.current_tab].scrollto(page_search['occurs'][0])
                    self.status_bar.update_left("Viewing result #1 for '%s'" % (query))
                    self.last_page_search = page_search  # keep this search
                else:
                    self.status_bar.update_left("No results for '%s'" % (query))
                    self.last_page_search = {'query':"", 'occurs':[], 'viewing':0}  # reset to no search

        self.entry_window.clear()
        self.text_entry = Textbox(self.entry_window, self.validate, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.display_current_tab()
        self.insert_mode = False
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def quit(self):
        self.update_timer.cancel()
        curses.endwin()
        sys.exit()
