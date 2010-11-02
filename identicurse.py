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
        self.main_window.scrollok(1)
        self.main_window.idlok(1)

        # TODO: pad = textpad.Textbox(scr) etc

        self.update_timelines()
        self.display_current_timeline()

        self.loop()

    def loop(self):
        running = True

        while running:
            input = self.main_window.getch()

            if input == ord("r"):
                update_current()
            elif input == ord("1"):
                self.current_timeline = "home"
            elif input == ord("2"):
                self.current_timeline = "mentions"
            elif input == ord("3"):
                self.current_timeline = "direct"
            elif input == ord("4"):
                self.current_timeline = "public"
            elif input == ord("q"):
                running = False

            self.display_current_timeline()
            self.main_window.refresh()

        self.quit();
        
    def update_timelines(self):
        self.timelines["home"] = self.conn.statuses_home_timeline(count=10, page=0)
        self.timelines["mentions"] = self.conn.statuses_mentions(count=10, page=0)
        self.timelines["direct"] = self.conn.direct_messages(count=10, page=0)
        self.timelines["public"] = self.conn.statuses_public_timeline()

    def display_current_timeline(self):
        self.main_window.erase()
        tl = self.timelines[self.current_timeline]

        y = 0
        c = 1
        for n in tl:
            if self.current_timeline == "direct":
                user = "none"
            else:
                user = unicode(n["user"]["screen_name"])

            self.main_window.addstr(y,0, unicode(str(c)))
            self.main_window.addstr(y,3, user)
            y += 1
            text = unicode(n["text"])
            self.main_window.addstr(y,4, text)
            y += 2
 
    def quit(self):
        curses.endwin()
        sys.exit()
