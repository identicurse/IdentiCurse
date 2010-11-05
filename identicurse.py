#!/usr/bin/env python

import os
import sys
import json
import re
import curses
from curses import textpad

from statusnet import StatusNet

import locale
locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

class Profile(object):
    def __init__(self, conn, window, id):
        self.conn = conn
        self.window = window
        self.id = id

        self.update()

    def update(self):
        self.profile = self.conn.users_show(screen_name=self.id)

    def display(self):
        self.window.erase()
        
        title = self.profile['screen_name'].capitalize().encode("utf-8") + "'s Profile"
        self.window.addstr(0, 4, title)
       
        if self.profile['name']:
            real_name = "Real Name: " + self.profile['name']
            self.window.addstr(2, 4, real_name)
       
        if self.profile['description']:
            bio = "Bio: " + self.profile['description']
            self.window.addstr(3, 4, bio)

        if self.profile['statuses_count']:
            notices_count = "Notices: " + str(self.profile['statuses_count'])
            self.window.addstr(4, 4, notices_count)

class Help(object):
    def __init__(self, window):
        self.window = window
        self.buffer = []
        self.start_line = 0
        self.update_buffer()

    def scrollup(self, n):
        if self.start_line == 0:
            pass
        else:
            self.start_line -= n

    def scrolldown(self, n):
        self.start_line += n

    def update(self):
        pass

    def update_buffer(self):
        self.buffer = open('README', 'r').read().split("\n")

    def display(self):
        self.window.erase()
        self.window.addstr("\n".join(self.buffer[self.start_line:self.window.getmaxyx()[0] - 3 + self.start_line]).encode("utf-8"))
        self.window.refresh()

class Timeline(object):
    def __init__(self, conn, window, timeline, type_params={}):
        self.conn = conn
        self.window = window
        self.timeline_type = timeline
        self.type_params = type_params  # dictionary to hold special parameters unique to individual timeline types

        self.buffer = []
        self.start_line = 0

        self.html_regex = re.compile("<(.|\n)*?>")  # compile this here and store it so we don't need to compile the regex every time 'source' is used

    def update(self):
        if self.timeline_type == "home":
            self.timeline = self.conn.statuses_home_timeline(count=25, page=0)
        elif self.timeline_type == "mentions":
            self.timeline  = self.conn.statuses_mentions(count=25, page=0)
        elif self.timeline_type == "direct":
            self.timeline = self.conn.direct_messages(count=25, page=0)
        elif self.timeline_type == "public":
            self.timeline = self.conn.statuses_public_timeline()
        elif self.timeline_type == "user":
            self.timeline = self.conn.statuses_user_timeline(user_id=self.type_params['user_id'], screen_name=self.type_params['screen_name'], count=25, page=0)
        elif self.timeline_type == "group":
            self.timeline = self.conn.statusnet_groups_timeline(group_id=self.type_params['group_id'], nickname=self.type_params['nickname'], count=25, page=0)
        elif self.timeline_type == "tag":
            self.timeline = self.conn.statusnet_tags_timeline(tag=self.type_params['tag'], count=25, page=0)
        elif self.timeline_type == "sentdirect":
            self.timeline = self.conn.direct_messages_sent(count=25, page=0)
        elif self.timeline_type == "favourites":
            self.timeline = self.conn.favorites(page=0)
        elif self.timeline_type == "search":
            self.timeline = self.conn.search(self.type_params['query'], page=0, standardise=True)

        self.update_buffer()

    def update_buffer(self):
        self.buffer = []

        maxx = self.window.getmaxyx()[1]
        c = 1

        for n in self.timeline:
            if "direct" in self.timeline_type:
                user = unicode("%s -> %s" % (n["sender"]["screen_name"], n["recipient"]["screen_name"]))
                source_msg = "" # source parameter cannot be retrieved from a direct, wtf?
            else:
                user = unicode(n["user"]["screen_name"])
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)    # strip out the link tag that identi.ca adds to some clients' source info
                if n["in_reply_to_status_id"] is not None:
                    source_msg += " [+]"
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1
            self.buffer[y] += ' ' * 3
            self.buffer[y] += user
            self.buffer[y] += ' ' * (maxx - ((len(source_msg) + (len(user)) + 6)))
            self.buffer[y] += source_msg

            try:
                self.buffer.append(n['text'])
            except UnicodeDecodeError:
                self.buffer += "Caution: Terminal too shit to display this notice"

            self.buffer.append("")
            self.buffer.append("")

            c += 1

    def scrollup(self, n):
        if self.start_line == 0:
            pass
        else:
            self.start_line -= n

    def scrolldown(self, n):
        self.start_line += n

    def display(self):
        self.window.erase()
        self.window.addstr("\n".join(self.buffer[self.start_line:self.window.getmaxyx()[0] - 3 + self.start_line]).encode("utf-8"))
        self.window.refresh()

class Context(object):
    def __init__(self, conn, window, notice_id):
        self.conn = conn
        self.window = window
        self.notice = notice_id
        self.timeline = []

        self.html_regex = re.compile("<(.|\n)*?>")  # compile this here and store it so we don't need to compile the regex every time 'source' is used

    def update(self):
        self.timeline = []
        next_id = self.notice
        while next_id is not None:
            self.timeline += [self.conn.statuses_show(id=next_id)]
            next_id = self.timeline[-1]['in_reply_to_status_id']

    def display(self):
        self.window.erase()

        y = 0
        c = 1

        maxc = self.window.getmaxyx()[0] / 3
        maxx = self.window.getmaxyx()[1]

        for n in self.timeline:
            user = unicode(n["user"]["screen_name"])
            raw_source_msg = "from %s" % (n["source"])
            source_msg = self.html_regex.sub("", raw_source_msg)    # strip out the link tag that identi.ca adds to some clients' source info
            if n["in_reply_to_status_id"] is not None:
                source_msg += " [+]"
            
            self.window.addstr(y, 0, str(c))
            self.window.addstr(y, 3, user)
            self.window.addstr(y, maxx - (len(source_msg) + 2), source_msg)  # right margin of 2 to match the left indentation
            y += 1

            try:
                text = self.html_regex.sub("", n["text"])
                self.window.addstr(y, 4, text.encode("utf-8"))
            except curses.error:
                self.window.addstr(y, 4, str("Caution: Terminal too shit to display this notice."))
            
            y += 2
            c += 1

            if c == maxc:
                break

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

        self.notice_window = self.main_window.subwin(y-6, x-4, 7, 5)
        
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
        for tab in self.tabs:
            tab.update()

    def display_current_tab(self):
        self.tabs[self.current_tab].display()

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
            
            for x in range(0, len(self.tabs)):
                if input == ord(str(x+1)):
                    self.current_tab = x

            self.display_current_tab()
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
                        id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["id"]

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
            else:
                self.conn.statuses_update(input, source="IdentiCurse")

        # Why doesn't textpad have a clear method!?
        self.entry_window.clear()
        self.text_entry = textpad.Textbox(self.entry_window, insert_mode=True)
        self.update_tabs()
        self.display_current_tab()
        
    def quit(self):
        curses.endwin()
        sys.exit()
