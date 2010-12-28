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

import os.path, re, sys, threading, datetime, locale, time_helper
DATETIME_FORMAT = "%a %b %d %H:%M:%S +0000 %Y"

class Buffer(list):
    def __init__(self):
        list.__init__(self)

    def append(self, item):
        if "\n" in item:  # sometimes there are newlines in the buffer's input, even when it's a dent. we need to remove them.
            for line in item.split("\n"):
                self.append(line)  # pass the line back in for further checking
        elif "\t" in item:  # if there are tabs in the input, it will display wider than the expected number of characters. convert them to spaces.
            item = "    ".join(item.split("\t"))
            self.append(item)  # pass the result back in for further checking
        else:  # we should only get here when we have a completely clean line
            list.append(self, item)
        
    def clear(self):
        self[:] = []

    def reflowed(self, width):
        """return a reflowed-for-width copy of the buffer as a list"""
        reflowed_buffer = []
        for line in self:
            while len(line) > width:
                reflowed_buffer.append(line[:width])
                line = line[width:]
            reflowed_buffer.append(line) # append whatever part of the line wasn't already added
        return reflowed_buffer

class TabUpdater(threading.Thread):
    def __init__(self, tabs, callback_object, callback_function):
        threading.Thread.__init__(self)
        self.daemon = True
        self.tabs = tabs
        self.callback_object = callback_object
        self.callback_function = callback_function

    def run (self):
        for tab in self.tabs:
            tab.update()
            if tab.active:
                tab.display()  # update the display of the tab if it's the foreground one

        fun = getattr(self.callback_object, self.callback_function)
        fun()

class Tab(object):
    def __init__(self, window):
        self.window = window
        self.buffer = Buffer()
        self.start_line = 0
        self.html_regex = re.compile("<(.|\n)*?>")
        self.page = 1
        self.active = False
        
    def prevpage(self, n=1):
        if n > 0:
            self.page -= n
            if self.page < 1:
                self.page = 1
                return False
            self.scrolldown(0)  # scroll to the end of the newer page, so the dent immediately after the start of the last page can be seen
        else:
            if self.page == 1:
                return False
            else:
                self.page = 1
                self.scrollup(0)
        return True
    
    def nextpage(self):
        self.page += 1
        self.scrollup(0)  # as in prevpage, only the other way around
        return True
    
    def scrollup(self, n):  # n == 0 indicates maximum scroll-up, i.e., scroll right to the top
        if not (n == 0):
            self.start_line -= n
            if self.start_line < 0:
                self.start_line = 0
        else:
            self.start_line = 0

    def scrolldown(self, n):  # n == 0 indicates maximum scroll-down, i.e., scroll right to the bottom
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if not (n == 0):
            self.start_line += n
            if self.start_line > len(self.buffer.reflowed(maxx - 2)) - (maxy - 3):
                self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)
        else:
            self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)

    def scrollto(self, n):  # attempt to get line number n as close to the top as possible unless already visible - this is less clean than the relative scrolls, so don't call it unless you *need* to go to a specific line.
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if (n >= self.start_line) and (n < (maxy - 3 + self.start_line)):  # if the line is already visible, bail out
            return
        if (n > self.start_line) and (n > len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)):
            self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)
        else:
            self.start_line = n

    def scrolltodent(self, n):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        dent_line = 0
        for line in self.buffer.reflowed(maxx - 2):
            if ("%d * " % (n + 1) in line) or ("%d   " % (n + 1) in line):
                break
            else:
                dent_line += 1
        self.scrollto(dent_line)

    def display(self):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        self.window.erase()
        self.window.addstr("\n".join(self.buffer.reflowed(maxx - 2)[self.start_line:maxy - 3 + self.start_line]).encode(sys.getfilesystemencoding(), "replace"))
        self.window.refresh()

class Help(Tab):
    def __init__(self, window, identicurse_path):
        self.name = "Help"
        self.path = os.path.join(identicurse_path, "README")
        Tab.__init__(self, window) 

    def update(self):
        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()
        self.buffer.append(open(self.path, 'r').read())

class Timeline(Tab):
    def __init__(self, conn, window, timeline, type_params={}, notice_limit=25, filters=[]):
        self.conn = conn
        self.timeline = []
        self.timeline_type = timeline
        self.type_params = type_params
        self.notice_limit = notice_limit
        self.filters = filters
        self.chosen_one = 0

        if self.timeline_type == "user":
            self.basename = "User (%s)" % self.type_params['screen_name']
        elif self.timeline_type == "tag":
            self.basename = "Tag (%s)" % self.type_params['tag']
        elif self.timeline_type == "group":
            self.basename = "Group (%s)" % self.type_params['nickname']
        elif self.timeline_type == "search":
            self.basename = "Search (%s)" % self.type_params['query']
        elif self.timeline_type == "sentdirect":
            self.basename = "Sent Directs"
        else:
            self.basename = self.timeline_type.capitalize()
        self.name = self.basename
        
        Tab.__init__(self, window)

    def update(self):
        self.timeline = []
        get_count = self.notice_limit - len(self.timeline)
        if self.timeline_type == "home":
            raw_timeline = self.conn.statuses_home_timeline(count=get_count, page=self.page)
        elif self.timeline_type == "mentions":
            raw_timeline = self.conn.statuses_mentions(count=get_count, page=self.page)
        elif self.timeline_type == "direct":
            raw_timeline = self.conn.direct_messages(count=get_count, page=self.page)
        elif self.timeline_type == "user":
            raw_timeline = self.conn.statuses_user_timeline(user_id=self.type_params['user_id'], screen_name=self.type_params['screen_name'], count=get_count, page=self.page)
        elif self.timeline_type == "group":
            raw_timeline = self.conn.statusnet_groups_timeline(group_id=self.type_params['group_id'], nickname=self.type_params['nickname'], count=get_count, page=self.page)
        elif self.timeline_type == "tag":
            raw_timeline = self.conn.statusnet_tags_timeline(tag=self.type_params['tag'], count=get_count, page=self.page)
        elif self.timeline_type == "sentdirect":
            raw_timeline = self.conn.direct_messages_sent(count=get_count, page=self.page)
        elif self.timeline_type == "public":
            raw_timeline = self.conn.statuses_public_timeline()
        elif self.timeline_type == "favourites":
            raw_timeline = self.conn.favorites(page=self.page)
        elif self.timeline_type == "search":
            raw_timeline = self.conn.search(self.type_params['query'], page=self.page, standardise=True)

        for notice in raw_timeline:
            passes_filters = True
            for filter_item in self.filters:
                if filter_item.lower() in notice['text'].lower():
                    passes_filters = False
                    break
            if passes_filters:
                self.timeline.append(notice)

        if self.page > 1:
            self.name = self.basename + "+%d" % (self.page - 1)
        else:
            self.name = self.basename
        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()

        maxx = self.window.getmaxyx()[1]
        c = 1

        for n in self.timeline:
            if "direct" in self.timeline_type:
                user = unicode("%s -> %s" % (n["sender"]["screen_name"], n["recipient"]["screen_name"]))
                source_msg = ""
            else:
                if "retweeted_status" in n:
                    user = "%s [ repeat by %s ]" % (n["retweeted_status"]["user"]["screen_name"], n["user"]["screen_name"])
                    n = n["retweeted_status"]
                else:
                    user = unicode(n["user"]["screen_name"])
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)
                repeat_msg = ""
                if n["in_reply_to_status_id"] is not None:
                    source_msg += " [+]"
            locale.setlocale(locale.LC_TIME, 'C')  # hacky fix because statusnet uses english timestrings regardless of locale
            datetime_notice = datetime.datetime.strptime(n['created_at'], DATETIME_FORMAT)
            locale.setlocale(locale.LC_TIME, '') # other half of the hacky fix
            time_msg = time_helper.format_time(time_helper.time_since(datetime_notice))
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1

            if (c - 1) == self.chosen_one:
                self.buffer[y] += ' * '
            else:
                self.buffer[y] += ' ' * 3

            self.buffer[y] += user
            self.buffer[y] += ' ' * (maxx - ((len(source_msg) + len(user) + (5 + len(str(c))))))
            self.buffer[y] += source_msg

            try:
                self.buffer.append(n['text'])
            except UnicodeDecodeError:
                self.buffer.append("Caution: Terminal too shit to display this notice.")

            self.buffer.append(" " * (maxx - (len(time_msg) + 2)))
            y = len(self.buffer) - 1
            self.buffer[y] += time_msg
            
            self.buffer.append("")
            self.buffer.append("")

            c += 1

class Context(Tab):
    def __init__(self, conn, window, notice_id):
        self.conn = conn
        self.notice = notice_id
        self.timeline = []
        self.chosen_one = 0

        self.name = "Context"

        Tab.__init__(self, window)

    def update(self):
        self.timeline = []
        next_id = self.notice

        while next_id is not None:
            self.timeline += [self.conn.statuses_show(id=next_id)]
            if "retweeted_status" in self.timeline[-1]:
                next_id = self.timeline[-1]['retweeted_status']['id']
            else:
                next_id = self.timeline[-1]['in_reply_to_status_id']

        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear() 

        c = 1

        maxx = self.window.getmaxyx()[1]

        for n in self.timeline:
            user = unicode(n["user"]["screen_name"])
            raw_source_msg = "from %s" % (n["source"])
            source_msg = self.html_regex.sub("", raw_source_msg)
            if n["in_reply_to_status_id"] is not None:
                source_msg += " [+]"
            elif "retweeted_status" in n:
                source_msg += " [~]"
            locale.setlocale(locale.LC_TIME, 'C')  # hacky fix because statusnet uses english timestrings regardless of locale
            datetime_notice = datetime.datetime.strptime(n['created_at'], DATETIME_FORMAT)
            locale.setlocale(locale.LC_TIME, '') # other half of the hacky fix
            time_msg = time_helper.format_time(time_helper.time_since(datetime_notice))
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1

            if (c - 1) == self.chosen_one:
                self.buffer[y] += ' * '
            else:
                self.buffer[y] += ' ' * 3
            self.buffer[y] += user
            self.buffer[y] += ' ' * (maxx - ((len(source_msg) + len(user) + (5 + len(str(c))))))
            self.buffer[y] += source_msg

            try:
                self.buffer.append(n['text'])
            except UnicodeDecodeError:
                self.buffer += "Caution: Terminal too shit to display this notice"

            self.buffer.append(" " * (maxx - (len(time_msg) + 2)))
            y = len(self.buffer) - 1
            self.buffer[y] += time_msg
            
            self.buffer.append("")
            self.buffer.append("")

            c += 1

class Profile(Tab):
    def __init__(self, conn, window, id):
        self.conn = conn
        self.id = id

        self.name = "Profile (%s)" % self.id

        Tab.__init__(self, window)

    def update(self):
        self.profile = self.conn.users_show(screen_name=self.id)
        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()
        self.buffer.append("@" + self.profile['screen_name'] + "'s Profile")
        self.buffer.append("")
        self.buffer.append("")

        if self.profile['name']:
            self.buffer.append("Real Name: " + self.profile['name'])
            self.buffer.append("")
       
        if self.profile['description']:
            self.buffer.append("Bio: " + self.profile['description'])
        if self.profile['location']:
            self.buffer.append("Location: " + self.profile['location'])
        if self.profile['url']:
            self.buffer.append("URL: " + self.profile['url'])
        if self.profile['id']:
            self.buffer.append("User ID: " + str(self.profile['id']))
        if self.profile['created_at']:
            self.buffer.append("Joined at: " + str(self.profile['created_at']))

            self.buffer.append("")

        if self.profile['followers_count']:
            self.buffer.append("Followed by: " + str(self.profile['followers_count']))
        if self.profile['friends_count']:
            self.buffer.append("Following: " + str(self.profile['friends_count']))
        if self.profile['following']:
            self.buffer.append("Followed by you: Yes")
        else:
            self.buffer.append("Followed by you: No")

        self.buffer.append("")

        if self.profile['favourites_count']:
            self.buffer.append("Favourites: " + str(self.profile['favourites_count']))
        if self.profile['statuses_count']:
            self.buffer.append("Notices: " + str(self.profile['statuses_count']))

            locale.setlocale(locale.LC_TIME, 'C')  # hacky fix because statusnet uses english timestrings regardless of locale
            datetime_joined = datetime.datetime.strptime(self.profile['created_at'], DATETIME_FORMAT)
            locale.setlocale(locale.LC_TIME, '') # other half of the hacky fix
            days_since_join = time_helper.single_unit(time_helper.time_since(datetime_joined), "days")['days']
            notices_per_day = float(self.profile['statuses_count']) / days_since_join

            self.buffer.append("Average daily notices: %0.2f" % (notices_per_day))
