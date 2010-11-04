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

    def update(self):
        pass

    def display(self):
        self.window.erase()

        self.window.addstr(0, 4, "IdentiCurse Help")

        self.window.addstr(2, 4, "Keybindings")
        self.window.addstr(4, 4, "1, 2, 3, 4 etc - Go to tab, initially open are 1. Home, 2. Replies, 3. Direct, 4. Public")
        self.window.addstr(5, 4, "q - Quit")
        self.window.addstr(6, 4, "r - Refresh timelines")
        self.window.addstr(7, 4, "x - Close current tab")
        self.window.addstr(8, 4, "i - Enter insert mode")

        self.window.addstr(10, 4, "Commands (to be typed in insert mode)")
        self.window.addstr(12, 4, "/reply [timeline item number] [message] - Reply to a notice (alias: /r)")
        self.window.addstr(13, 4, "/reply [username] [message] - Mention a user (alias: /r)")
        self.window.addstr(14, 4, "/fav [timeline item number] - Favourite a notice (alias: /f)")
        self.window.addstr(15, 4, "/repeat [timeline item number] - Repeat a notice (alias: /rt)")
        self.window.addstr(16, 4, "/direct [username] - Direct Message a user (alias: /dm)")
        self.window.addstr(17, 4, "/delete [timeline item number] - Delete a notice (alias: /d, /del)")
        self.window.addstr(18, 4, "/profile [timeline item number] - Open the profile of the notice's poster (alias: /p)")
        self.window.addstr(19, 4, "/profile [username] - Open a user's profile (alias: /p)")

class Timeline(object):
    def __init__(self, conn, window, timeline):
        self.conn = conn
        self.window = window
        self.timeline_type = timeline

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

    def display(self):
        self.window.erase()

        y = 0
        c = 1

        maxc = self.window.getmaxyx()[0] / 3
        maxx = self.window.getmaxyx()[1]

        for n in self.timeline:
            if self.timeline_type == "direct":
                user = unicode(n["sender"]["screen_name"])
                source_msg = "" # source parameter cannot be retrieved from a direct, wtf?
            else:
                user = unicode(n["user"]["screen_name"])
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)    # strip out the link tag that identi.ca adds to some clients' source info
            
            self.window.addstr(y, 0, str(c))
            self.window.addstr(y, 3, user)
            self.window.addstr(y, maxx - (len(source_msg) + 2), source_msg)  # right margin of 2 to match the left indentation
            y += 1
            text = n["text"]

            try:
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
        self.main_window.scrollok(1)
        self.main_window.idlok(1)

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

            if input == ord("r"):
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
                
                if tokens[0] == "/reply" or tokens[0] == "/r":
                    # Yeuch
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
                elif tokens[0] == "/fav" or tokens[0] == "/f":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.favorites_create(id)
                elif tokens[0] == "/repeat" or tokens[0] == "/rt":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.statuses_retweet(id, source="IdentiCurse")
                elif tokens[0] == "/direct" or tokens[0] == "/dm" or tokens[0] == "/d":
                    screen_name = tokens[1]
                    if screen_name[0] == "@":
                        screen_name = screen_name[1:]
                    id = self.conn.users_show(screen_name=screen_name)['id']
                    self.conn.direct_messages_new(screen_name, id, " ".join(tokens[2:]), source="IdentiCurse")
                elif tokens[0] == "/delete" or tokens[0] == "/del":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['id']
                    self.conn.statuses_destroy(id)
                elif tokens[0] == "/profile" or tokens[0] == "/p":
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
                elif tokens[0] == "/spamreport" or tokens[0] == "/sr" or tokens[0] == "/nuke" or tokens[0] == "/kill" or tokens[0] == "/burn":
                    id = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]['user']['id']
                    username = self.tabs[self.current_tab].timeline[int(tokens[1]) - 1]["user"]["screen_name"]
                    status = "@support !sr @%s UID %d %s" % (username, id, " ".join(tokens[2:]))
                    self.conn.statuses_update(status, "IdentiCurse")
                    self.conn.blocks_create(user_id=id, screen_name=username)
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
