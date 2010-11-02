#!/usr/bin/env python

import os
import sys
import curses
from curses import textpad

#import locale
#locale.setlocale(locale.LC_ALL, '')
#code = locale.getpreferredencoding()

class IdentiCurse(object):
    """Contains Main IdentiCurse application"""
    
    def __init__(self, config_path):

        # TODO: Load config
        self.config = 

        # TODO: Make StatusNet conn
        self.conn = 

        self.timelines = { 
            "home": [],
            "mentions": [],
            "direct": [],
            "public": [] 
        }
        self.current_timeline = "home"
        
        curses.wrapper(self.initialise)

    def initialise(self):
        curses.noecho()
        curses.cbreak()

        y, x = scr.getmaxyx()

        self.main_window = scr.subwin(y-1, x, 1, 0)
        self.main_window.scrollok(1)
        self.main_window.idlok(1)

        # TODO: pad = textpad.Textbox(scr) etc

        self.update_timelines()
        self.display_current_timeline()

        self.loop()

    def loop(scr):
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
        timelines["home"] = self.conn.get_home()
        timelines["mentions"] = self.conn.get_mentions()
        timelines["direct"] = self.conn.get_direct()
        timelines["public"] = self.conn.get_public()

    def display_current_timeline(self):
        # TODO: Make work
        win.erase()
        current = config["current_tl"]
        tl = timelines[current]
        y = 0
        c = 1
        for n in tl:
            if current == "direct":
                pass
            else:
                if config["show_names"]:
                    user = n["user"]["name"]
                else:
                    user = m["user"]["screen_name"]
                win.addstr(y,0, str(c))
                win.addstr(y,3, user)
            y += 1
            text = str(n["text"])
            win.addstr(y,4, text)
            y += 2
 
    def quit():
        curses.endwin()
        sys.exit()

    
