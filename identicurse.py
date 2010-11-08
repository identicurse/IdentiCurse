#!/usr/bin/env python

import os, sys, json, curses, locale
from threading import Timer
from curses import textpad
import urllib2

from statusnet import StatusNet
from tabbage import *
from statusbar import StatusBar

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self):
        config_file = os.path.join(os.path.expanduser("~") ,".identicurse")
        try:
            if os.path.exists(config_file):
                self.config = json.loads(open(config_file).read())
            else:
                config_file = "config.json"
                self.config = json.loads(open(config_file).read())
        except:
            sys.exit("ERROR: Couldn't read config file.")

        try:
            self.conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])
        except Exception as errmsg:
            sys.exit("ERROR: Couldn't establish connection: %s" % (errmsg))

        self.insert_mode = False
        curses.wrapper(self.initialise)

    def redraw(self):
        self.screen.erase()
        self.y, self.x = self.screen.getmaxyx()
        self.last_char = ""

        self.main_window = self.screen.subwin(self.y-2, self.x-3, 2, 2)
        self.main_window.keypad(1)
        self.main_window.box(0, 0)

        y, x = self.main_window.getmaxyx()

        if self.conn.length_limit == 0:
            entry_lines = 3
        else:
            entry_lines = (self.conn.length_limit / x) + 1

        self.entry_window = self.main_window.subwin(entry_lines, x-10, 4, 5)
        self.text_entry = textpad.Textbox(self.entry_window, insert_mode=True)
        self.text_entry.stripspaces = 1

        self.notice_window = self.main_window.subwin(y-7, x-4, 5 + entry_lines, 5)

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
                self.tabs.append(Timeline(self.conn, self.notice_window, "home"))
            if tab[0] == "mentions":
                self.tabs.append(Timeline(self.conn, self.notice_window, "mentions"))
            if tab[0] == "direct":
                self.tabs.append(Timeline(self.conn, self.notice_window, "direct"))
            if tab[0] == "public":
                self.tabs.append(Timeline(self.conn, self.notice_window, "public"))
            if tab[0] == "profile":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                self.tabs.append(Profile(self.conn, self.notice_window, screen_name))
            if tab[0] == "sentdirect":
                self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect"))
            if tab[0] == "user":
                screen_name = tab[1]
                if screen_name[0] == "@":
                    screen_name = screen_name[1:]
                user_id = self.conn.users_show(screen_name=screen_name)['id']
                self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'screen_name':screen_name, 'user_id':user_id}))
            if tab[0] == "group":
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
                self.tabs.append(Help(self.notice_window))

        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

        self.current_tab = 0
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
            
            self.display_current_tab()

    def loop(self):
        running = True

        while running:
            input = self.main_window.getch()

            if input == curses.KEY_UP:
                self.tabs[self.current_tab].scrollup(1)
                self.display_current_tab()
            elif input == curses.KEY_PPAGE:
                self.tabs[self.current_tab].scrollup(self.main_window.getmaxyx()[0] - 11) # the 11 offset gives 2 lines of overlap between the pre-scroll view and post-scroll view
                self.display_current_tab()
            elif input == curses.KEY_DOWN:
                self.tabs[self.current_tab].scrolldown(1)
                self.display_current_tab()
            elif input == curses.KEY_NPAGE:
                self.tabs[self.current_tab].scrolldown(self.main_window.getmaxyx()[0] - 11) # as above
                self.display_current_tab()
            if input == curses.KEY_LEFT:
                if self.tabs[self.current_tab].prevpage():
                    self.status_bar.update_left("Moving to newer page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            if input == curses.KEY_RIGHT:
                if self.tabs[self.current_tab].nextpage():
                    self.status_bar.update_left("Moving to older page...")
                    self.tabs[self.current_tab].update()
                    self.status_bar.update_left("Doing nothing.")
            elif input == ord("r"):
                self.update_tabs()
            elif input == ord("i"):
                self.update_timer.cancel()
                self.insert_mode = True
                self.status_bar.update_left("Editing Dent: " + str(self.conn.length_limit) + " characters remaining")
                self.parse_input(self.text_entry.edit(self.validate))
            elif input == ord("q"):
                running = False
            elif input == ord("x"):
                self.close_current_tab()
            elif input == ord("h"):
                self.tabs.append(Help(self.notice_window))
                self.current_tab = len(self.tabs) - 1
                self.tab_order.insert(0, self.current_tab)
                self.tabs[self.current_tab].update()
            
            for x in range(0, len(self.tabs)):
                if input == ord(str(x+1)):
                    self.tab_order.insert(0, self.tab_order.pop(self.tab_order.index(x)))
                    self.current_tab = x

            y, x = self.screen.getmaxyx()
            if y != self.y or x != self.x:
                self.redraw()
                self.update_tab_buffers()

            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, ch):
        """ I hate ncurses so god damned much """
        if ch == 127:
            self.text_entry.do_command(263)
        
        text = self.text_entry.gather().rstrip()
        length = len(text) + 1

        if self.last_char == ord(" "):
            if ch == 22:
                self.validate(ch)
            else:
                self.last_char = ""
                self.text_entry.do_command(" ")
                length += 1

        self.status_bar.update_left("Editing Dent: " + str(self.conn.length_limit - length) + " characters remaining")

        self.last_char = ch
        return ch

    def parse_input(self, input):
        if len(input) > 0:      # don't do anything if the user didn't enter anything
            input = input.rstrip()

            if input[0] == "/":
                tokens = input.split(" ")

                if tokens[0] in self.config["aliases"]:
                    tokens[0] = self.config["aliases"][tokens[0]]
                
                if tokens[0] == "/reply":
                    self.status_bar.update_left("Posting Reply...")

                    try:
                        float(tokens[1])
                    except ValueError:
                        user = tokens[1]
                        if user[0] == "@":
                        	user = user[1:]
                        id = 0  # this is not a reply to a dent
                    else:
                        user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    status = "@" + user + " " + " ".join(tokens[2:])

                    try:
                        self.conn.statuses_update(status, "IdentiCurse", int(id))
                    except Exception as errmsg:
                        self.status_bar.timed_update_left("ERROR: Couldn't post status: %s" % (errmsg))

                elif tokens[0] == "/favourite":
                    self.status_bar.update_left("Favouriting Notice...")
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.favorites_create(id)

                elif tokens[0] == "/repeat":
                    self.status_bar.update_left("Repeating Notice...")
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.statuses_retweet(id, source="IdentiCurse")

                elif tokens[0] == "/direct":
                    self.status_bar.update_left("Sending Direct...")
                    screen_name = tokens[1]
                    if screen_name[0] == "@":
                        screen_name = screen_name[1:]
                    id = self.conn.users_show(screen_name=screen_name)['id']
                    self.conn.direct_messages_new(screen_name, id, " ".join(tokens[2:]), source="IdentiCurse")

                elif tokens[0] == "/delete":
                    self.status_bar.update_left("Deleting Notice...")
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    try:
                        self.conn.statuses_destroy(id)
                    except urllib2.HTTPError, e:
                        if e.code == 403:
                            self.status_bar.timed_update_left("ERROR: You cannot delete others' statuses.")

                elif tokens[0] == "/profile":
                    self.status_bar.update_left("Loading Profile...")
                    # Yeuch
                    try:
                        float(tokens[1])
                    except ValueError:
                        user = tokens[1]
                        if user[0] == "@":
                        	user = user[1:]
                    else:
                        user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]

                    self.tabs.append(Profile(self.conn, self.notice_window,user))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)

                elif tokens[0] == "/spamreport":
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
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                        username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                    status = "@support !sr @%s UID %d %s" % (username, id, " ".join(tokens[2:]))
                    self.conn.statuses_update(status, "IdentiCurse")
                    self.conn.blocks_create(user_id=id, screen_name=username)

                elif tokens[0] == "/block":
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
                            user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                            id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                        self.conn.blocks_create(user_id=id, screen_name=user)

                elif tokens[0] == "/unblock":
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
                            user = self.tabs[self.current_tab].timeline[int(token) - 1]["user"]["screen_name"]
                            id = self.tabs[self.current_tab].timeline[int(token) - 1]['user']['id']
                        self.conn.blocks_destroy(user_id=id, screen_name=user)

                elif tokens[0] == "/user":
                    self.status_bar.update_left("Loading User Timeline...")
                    try:
                        # Yeuch
                        try:
                            float(tokens[1])
                        except ValueError:
                            user = tokens[1]
                            if user[0] == "@":
                        	user = user[1:]
                            id = self.conn.users_show(screen_name=user)['id']
                        else:
                            user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                            id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["id"]
                        
                        self.tabs.append(Timeline(self.conn, self.notice_window, "user", {'user_id':id, 'screen_name':user}))
                        self.current_tab = len(self.tabs) - 1
                        self.tab_order.insert(0, self.current_tab)
                    except urllib2.HTTPError, e:
                        if e.code == 404:
                            self.status_bar.timed_update_left("ERROR: Couldn't open timeline: No such user")

                elif tokens[0] == "/context":
                    self.status_bar.update_left("Loading Context...")
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]

                    self.tabs.append(Context(self.conn, self.notice_window, id))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)

                elif tokens[0] == "/subscribe":
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
                        user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]

                    self.conn.friendships_create(user_id=id, screen_name=user)
                    
                elif tokens[0] == "/unsubscribe":
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
                        user = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]

                    self.conn.friendships_destroy(user_id=id, screen_name=user)

                elif tokens[0] == "/group":
                    self.status_bar.update_left("Loading Group Timeline...")
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'group_id':id, 'nickname':group}))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)

                elif tokens[0] == "/groupjoin":
                    self.status_bar.update_left("Joining Group...")
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.conn.statusnet_groups_join(group_id=id, nickname=group)

                elif tokens[0] == "/groupleave":
                    self.status_bar.update_left("Leaving Group...")
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.conn.statusnet_groups_leave(group_id=id, nickname=group)

                elif tokens[0] == "/tag":
                    self.status_bar.update_left("Loading Tag Timeline...")
                    tag = tokens[1]
                    if tag[0] == "#":
                        tag = tag[1:]

                    self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)

                elif tokens[0] == "/sentdirects":
                    self.status_bar.update_left("Loading Sent Directs...")
                    self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)

                elif tokens[0] == "/favourites":
                    self.status_bar.update_left("Loading Favourites...")
                    self.tabs.append(Timeline(self.conn, self.notice_window, "favourites"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                    
                elif tokens[0] == "/search":
                    self.status_bar.update_left("Searching...")
                    query = " ".join(tokens[1:])
                    self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':query}))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                
                elif tokens[0] == "/home":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "home"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                
                elif tokens[0] == "/mentions":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "mentions"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                
                elif tokens[0] == "/directs":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "direct"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                
                elif tokens[0] == "/public":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "public"))
                    self.current_tab = len(self.tabs) - 1
                    self.tab_order.insert(0, self.current_tab)
                    
                elif tokens[0] == "/config":
                    keys, value = tokens[1].split('.'), " ".join(tokens[2:])
                    if len(keys) == 2:      # there has to be a clean way to avoid hardcoded len checks, but I can't think what right now, and technically it works for all currently valid config keys
                        self.config[keys[0]][keys[1]] = value
                    else:
                        self.config[keys[0]] = value
                    open('config.json', 'w').write(json.dumps(self.config, indent=4))
                
                self.status_bar.update_left("Doing nothing.")
            else:
                self.status_bar.update_left("Posting Notice...")
                self.conn.statuses_update(input, source="IdentiCurse")

        self.entry_window.clear()
        self.text_entry = textpad.Textbox(self.entry_window, insert_mode=True)
        self.text_entry.stripspaces = 1
        self.insert_mode = False
        self.update_tabs()
        self.display_current_tab()
        self.insert_mode = False
        self.status_bar.update_left("Doing nothing.")
        self.update_timer = Timer(self.config['update_interval'], self.update_tabs)
        self.update_timer.start()

    def quit(self):
        self.update_timer.cancel()
        curses.endwin()
        sys.exit()
