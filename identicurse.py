#!/usr/bin/env python

import os
import sys
import json
import curses
from curses import textpad

from statusnet import StatusNet

import locale
locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self):

        self.config = json.loads(open('config.json').read())
        self.conn = StatusNet(self.config['api_path'], self.config['username'], self.config['password'])

        self.timelines = { 
            "home": [],
            "mentions": [],
            "direct": [],
            "public": [] 
        }
        self.current_timeline = "home"
        
        curses.wrapper(self.initialise)

    def initialise(self, screen):
        curses.noecho()
        curses.cbreak()

        y, x = screen.getmaxyx()
        self.main_window = screen.subwin(y-1, x, 1, 0)

        y, x = self.main_window.getmaxyx()
        self.entry_window = self.main_window.subwin(4, x, 1, 0)
        self.text_entry = textpad.Textbox(self.entry_window)

        self.notice_window = self.main_window.subwin(y-6, x, 5, 0)
        self.notice_window.box()

        self.main_window.scrollok(1)
        self.main_window.idlok(1)
        self.main_window.erase()

        self.update_timelines()
        self.display_current_timeline()

        self.loop()

    def loop(self):
        running = True

        while running:
            input = self.main_window.getch()

            if input == ord("r"):
                self.update_timelines()
                self.update_current()
            elif input == ord("1"):
                self.current_timeline = "home"
            elif input == ord("2"):
                self.current_timeline = "mentions"
            elif input == ord("3"):
                self.current_timeline = "direct"
            elif input == ord("4"):
                self.current_timeline = "public"
            elif input == ord("i"):
                self.parse_input(self.text_entry.edit())
            elif input == ord("q"):
                running = False

            self.display_current_timeline()
            self.main_window.refresh()

        self.quit();

    def parse_input(self, input):
        if input[0] == "/":
            tokens = input.split(" ")

            if tokens[0] == "/reply" or tokens[0] == "/r":
                id = self.timelines[self.current_timeline][int(tokens[1]) - 1]['id']
                username = self.timelines[self.current_timeline][int(tokens[1]) - 1]["user"]["screen_name"]
                status = "@" + username + " " + " ".join(tokens[2:])
                self.conn.statuses_update(status, "IdentiCurse", int(id))
            elif tokens[0] == "/fav" or tokens[0] == "/f":
                id = self.timelines[self.current_timeline][int(tokens[1]) - 1]['id']
                self.conn.favorites_create(id)
            elif tokens[0] == "/repeat" or tokens[0] == "/rt":
                id = self.timelines[self.current_timeline][int(tokens[1]) - 1]['id']
                self.conn.statuses_retweet(id)

        else:
            self.conn.statuses_update(input, source="IdentiCurse")

        # Why doesn't textpad have a clear method!?
        self.entry_window.clear()
        self.text_entry = textpad.Textbox(self.entry_window)
        
    def update_current(self):
        if self.current_timeline == "home":
            self.timelines["home"] = self.conn.statuses_home_timeline(count=20, page=0)
        elif self.current_timeline == "mentions":
            self.timelines["mentions"] = self.conn.statuses_mentions(count=20, page=0)
        elif self.current_timeline == "direct":
            self.timelines["direct"] = self.conn.direct_messages(count=20, page=0)
        elif self.current_timeline == "public":
            self.timelines["public"] = self.conn.statuses_public_timeline()

    def update_timelines(self):
        self.timelines["home"] = self.conn.statuses_home_timeline(count=20, page=0)
        self.timelines["mentions"] = self.conn.statuses_mentions(count=20, page=0)
        self.timelines["direct"] = self.conn.direct_messages(count=20, page=0)
        self.timelines["public"] = self.conn.statuses_public_timeline()

    def display_current_timeline(self):
        self.notice_window.erase()
        tl = self.timelines[self.current_timeline]

        y = 0
        c = 1

        maxc = self.notice_window.getmaxyx()[0] / 3

        for n in tl:
            if self.current_timeline == "direct":
                user = "none"
            else:
                user = unicode(n["user"]["screen_name"])

            self.notice_window.addstr(y,0, str(c))
            self.notice_window.addstr(y,3, user)
            y += 1
            text = n["text"]

            try:
                self.notice_window.addstr(y,4, text.encode("utf-8"))
            except curses.error:
                self.notice_window.addstr(y,4, str("Caution: Terminal too shit to display this notice."))
            
            y += 2
            c += 1

            if c == maxc:
                break
                
 
    def quit(self):
        curses.endwin()
        sys.exit()
