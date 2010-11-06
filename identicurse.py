#!/usr/bin/env python

import os, sys, json, curses, locale
from curses import textpad

from statusnet import StatusNet
from tabbage import *

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

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

    def update(self):
        self.window.erase()
        self.window.addstr(0, 0, self.left_text)
        right_x = self.window.getmaxyx()[1] - (len(self.right_text) + 3)
        self.window.addstr(0, right_x, self.right_text)
        self.window.refresh()

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self):
        self.config = json.loads(open('config.json').read())
        self.conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])
        curses.wrapper(self.initialise)

    def initialise(self, screen):
        curses.noecho()
        curses.cbreak()

        y, x = screen.getmaxyx()
        self.main_window = screen.subwin(y-2, x-3, 2, 2)
        self.main_window.box(0, 0)
        self.main_window.keypad(1)

        y, x = self.main_window.getmaxyx()
        self.entry_window = self.main_window.subwin(1, x-10, 4, 5)
        self.text_entry = textpad.Textbox(self.entry_window, insert_mode=True)

        self.notice_window = self.main_window.subwin(y-7, x-4, 6, 5)

        self.status_window = self.main_window.subwin(1, x-3, y, 5)
        self.status_bar = StatusBar(self.status_window)

        self.status_bar.update_left("Welcome to IdentiCurse")

        
        self.tabs = [
            Timeline(self.conn, self.notice_window, "home"),
            Timeline(self.conn, self.notice_window, "mentions"),
            Timeline(self.conn, self.notice_window, "direct"),
            Timeline(self.conn, self.notice_window, "public")
        ]
        self.current_tab = 0

        self.update_tabs()
        self.display_current_tab()

        self.loop()

    def update_tabs(self):
        self.status_bar.update_left("Updating Timelines...")
        for tab in self.tabs:
            tab.update()
        self.status_bar.update_left("Doing nothing.")

    def display_current_tab(self):
        self.tabs[self.current_tab].display()
        self.status_bar.update_right("Tab " + str(self.current_tab + 1) + ": " + self.tabs[self.current_tab].name)

    def close_current_tab(self):
        # This will die if on tab 0, obviously. TODO: Fix
        del self.tabs[self.current_tab]
        self.current_tab -= 1
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
            elif input == ord("r"):
                self.update_tabs()
            elif input == ord("i"):
                self.parse_input(self.text_entry.edit(self.validate))
            elif input == ord("q"):
                running = False
            elif input == ord("x"):
                self.close_current_tab()
            elif input == ord("h"):
                self.tabs.append(Help(self.notice_window))
                self.current_tab = len(self.tabs) - 1
                self.tabs[self.current_tab].update()
            
            for x in range(0, len(self.tabs)):
                if input == ord(str(x+1)):
                    self.current_tab = x

            self.display_current_tab()
            self.status_window.refresh()
            self.main_window.refresh()

        self.quit();

    def validate(self, ch):
        if ch == 127:
            self.text_entry.do_command(263)
        else:
            return ch

    def parse_input(self, input):
        if len(input) > 0:      # don't do anything if the user didn't enter anything
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

                    self.conn.statuses_update(status, "IdentiCurse", int(id))

                elif tokens[0] == "/favourite":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.favorites_create(id)

                elif tokens[0] == "/repeat":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.statuses_retweet(id, source="IdentiCurse")

                elif tokens[0] == "/direct":
                    screen_name = tokens[1]
                    if screen_name[0] == "@":
                        screen_name = screen_name[1:]
                    id = self.conn.users_show(screen_name=screen_name)['id']
                    self.conn.direct_messages_new(screen_name, id, " ".join(tokens[2:]), source="IdentiCurse")

                elif tokens[0] == "/delete":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.statuses_destroy(id)

                elif tokens[0] == "/profile":
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

                elif tokens[0] == "/spamreport":

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
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                    self.conn.blocks_create(user_id=id, screen_name=username)
                elif tokens[0] == "/unblock":
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
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                    self.conn.blocks_destroy(user_id=id, screen_name=username)
                elif tokens[0] == "/user":
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

                elif tokens[0] == "/context":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]

                    self.tabs.append(Context(self.conn, self.notice_window, id))
                    self.current_tab = len(self.tabs) - 1
                elif tokens[0] == "/subscribe":
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
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.tabs.append(Timeline(self.conn, self.notice_window, "group", {'group_id':id, 'nickname':group}))
                    self.current_tab = len(self.tabs) - 1

                elif tokens[0] == "/groupjoin":
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.conn.statusnet_groups_join(group_id=id, nickname=group)

                elif tokens[0] == "/groupleave":
                    group = tokens[1]
                    if group[0] == "!":
                        group = group[1:]
                    id = int(self.conn.statusnet_groups_show(nickname=group)['id'])

                    self.conn.statusnet_groups_leave(group_id=id, nickname=group)
                elif tokens[0] == "/tag":
                    tag = tokens[1]
                    if tag[0] == "#":
                        tag = tag[1:]

                    self.tabs.append(Timeline(self.conn, self.notice_window, "tag", {'tag':tag}))
                    self.current_tab = len(self.tabs) - 1

                elif tokens[0] == "/sentdirects":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "sentdirect"))
                    self.current_tab = len(self.tabs) - 1

                elif tokens[0] == "/favourites":
                    self.tabs.append(Timeline(self.conn, self.notice_window, "favourites"))
                    self.current_tab = len(self.tabs) - 1
                elif tokens[0] == "/search":
                    query = " ".join(tokens[1:])
                    self.tabs.append(Timeline(self.conn, self.notice_window, "search", {'query':query}))
                    self.current_tab = len(self.tabs) - 1
                
                self.status_bar.update_left("Doing nothing.")
            else:
                self.status_bar.update_left("Posting Notice...")
                self.conn.statuses_update(input, source="IdentiCurse")

        # Why doesn't textpad have a clear method!?
        self.entry_window.clear()
        self.text_entry = textpad.Textbox(self.entry_window, insert_mode=True)
        self.update_tabs()
        self.display_current_tab()
        
    def quit(self):
        curses.endwin()
        sys.exit()
