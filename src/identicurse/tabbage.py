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

import os.path, re, sys, threading, datetime, locale, time_helper, curses, random, identicurse
DATETIME_FORMAT = "%a %b %d %H:%M:%S +0000 %Y"

class Buffer(list):
    def __init__(self):
        list.__init__(self)

    def append(self, item):
        clean_item = []
        for block in item:
            clean_blocks = []
            if "\n" in block[0]:
                for sub_block in block[0].split("\n"):
                    clean_blocks.append((sub_block, block[1]))
            else:
                clean_blocks.append(block)
            for block in clean_blocks: 
                if "\t" in block[0]:
                    block = ("    ".join(block[0].split("\t")), block[1])
                clean_item.append(block)
        list.append(self, clean_item)
        
    def clear(self):
        self[:] = []

    def reflowed(self, width):
        """ Return a reflowed-for-width copy of the buffer as a list. """
        reflowed_buffer = []

        for line in self:
            reflowed_buffer.append([])
            line_length = 0
            for block in line:
                if (len(block[0]) + line_length) > width:
                    overlong_by = (len(block[0]) + line_length) - width
                    reflowed_buffer[-1].append((block[0][:len(block[0])-overlong_by], block[1]))
                    reflowed_buffer.append([])
                    reflowed_buffer[-1].append((block[0][len(block[0])-overlong_by:], block[1]))
                    line_length = len(reflowed_buffer[-1][-1][0])
                else:
                    reflowed_buffer[-1].append(block)
                    line_length += len(block[0])

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

    def scrollto(self, n, force_top=True):  # attempt to get line number n as close to the top as possible (unless already visible, if force_top==False) - this is less clean than the relative scrolls, so don't call it unless you *need* to go to a specific line.
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if (n >= self.start_line) and (n < (maxy - 3 + self.start_line)) and not force_top:  # if the line is already visible and force_top==False, bail out
            return
        if (n > self.start_line) and (n > len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)):
            self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)
        else:
            self.start_line = n

    def scrolltodent(self, n):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if n < 9:
            nout = " " + str(n+1)
        else:
            nout = str(n+1)
        dent_line = 0
        found_dent = False
        for line in self.buffer.reflowed(maxx - 2):
            for block in line:
                if block[1] == identicurse.colour_fields['notice_count'] and block[0] == nout:
                    self.scrollto(dent_line, force_top=False)
                    return
            dent_line += 1
        self.scrollto(dent_line, force_top=False)

    def display(self):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        self.window.erase()

        #buffer = self.buffer.reflowed(maxx - 2)
        for line in self.buffer[self.start_line:maxy - 3 + self.start_line]:
            for (part, attr) in line:
                self.window.addstr(part.encode(sys.getfilesystemencoding(), "replace"), curses.color_pair(attr))
            self.window.addstr("\n")
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
        #for l in open(self.path, 'r').readline():

class Timeline(Tab):
    def __init__(self, conn, window, timeline, type_params={}, notice_limit=25, filters=[], compact_style=False, user_rainbow=False):
        self.conn = conn
        self.timeline = []
        self.user_cache = {}
        self.timeline_type = timeline
        self.type_params = type_params
        self.notice_limit = notice_limit
        self.filters = filters
        self.compact_style = compact_style
        self.user_rainbow = user_rainbow
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

            if self.compact_style:
                time_msg = time_helper.format_time(time_helper.time_since(datetime_notice), short_form=True)
            else:
                time_msg = time_helper.format_time(time_helper.time_since(datetime_notice))

            if not user in self.user_cache:
                self.user_cache[user] = random.choice(identicurse.base_colours.items())[1]
           
            # Build the line
            line = []

            if c < 10:
                cout = " " + str(c)
            else:
                cout = str(c)
            line.append((cout, identicurse.colour_fields["notice_count"]))

            if (c - 1) == self.chosen_one:
                line.append((' * ', identicurse.colour_fields["selector"]))
            else:
                line.append((' ' * 3, identicurse.colour_fields["selector"]))

            if self.user_rainbow:
                line.append((user, self.user_cache[user]))
            else:
                line.append((user, identicurse.colour_fields["username"]))

            if self.compact_style:
                line.append((' ' * (maxx - ((len(source_msg) + len(time_msg) + len(user) + (6 + len(cout))))), identicurse.colour_fields["none"]))
                line.append((time_msg, identicurse.colour_fields["time"]))
                line.append((' ', identicurse.colour_fields["none"]))
                line.append((source_msg, identicurse.colour_fields["source"]))
            else:
                line.append((' ' * (maxx - ((len(source_msg) + len(user) + (5 + len(cout))))), identicurse.colour_fields["none"]))
                line.append(source_msg, identicurse.colour_fields["source"])

            self.buffer.append(line)

            if self.user_rainbow:
                line = []

                notice_parts = re.split(r'(@(\w+))', n['text'])
                wtf = False
                for part in notice_parts:
                    if wtf == True:
                        wtf = False
                        continue

                    part_list = list(part)
                    if len(part_list) > 0:
                        if part_list[0] == '@':
                            wtf = True
                            username = str("".join(part_list[1:]))
                            if not username in self.user_cache:
                                self.user_cache[username] = random.choice(identicurse.base_colours.items())[1]
                            line.append((part, self.user_cache[username]))
                        else:
                            line.append((part, identicurse.colour_fields["notice"]))

                self.buffer.append(line)

            else:
                try:
                    self.buffer.append([(n['text'], identicurse.colour_fields["notice"])])
                except UnicodeDecodeError:
                    self.buffer.append([("Caution: Terminal too shit to display this notice.", identicurse.colour_fields["none"])])

            if not self.compact_style:
                line = []
                line.append((" " * (maxx - (len(time_msg) + 2)), identicurse.colour_fields["time"]))
                line.append((time_msg, identicurse.colour_fields["none"]))
                
                self.buffer.append(line)
                self.buffer.append([])

            self.buffer.append([])

            c += 1

class Context(Tab):
    def __init__(self, conn, window, notice_id, compact_style=False):
        self.conn = conn
        self.notice = notice_id
        self.timeline = []
        self.compact_style = compact_style
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
            if "retweeted_status" in n:
                user = "%s [ repeat by %s ]" % (n["retweeted_status"]["user"]["screen_name"], n["user"]["screen_name"])
                n = n["retweeted_status"]
            else:
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
            if self.compact_style:
                time_msg = time_helper.format_time(time_helper.time_since(datetime_notice), short_form=True)
            else:
                time_msg = time_helper.format_time(time_helper.time_since(datetime_notice))
            
            line = []

            if c < 10:
                cout = " " + str(c)
            else:
                cout = str(c)
            line.append((cout, identicurse.colour_fields["notice_count"]))
            
            if (c - 1) == self.chosen_one:
                line.append((' * ', identicurse.colour_fields["selector"]))
            else:
                line.append((' ' * 3, identicurse.colour_fields["selector"]))

            line.append((user, identicurse.colour_fields["username"]))
            
            if self.compact_style:
                line.append((' ' * (maxx - ((len(source_msg) + len(time_msg) + len(user) + (6 + len(cout))))), identicurse.colour_fields["none"]))
                line.append((time_msg, identicurse.colour_fields["time"]))
                line.append((' ', identicurse.colour_fields["none"]))
                line.append((source_msg, identicurse.colour_fields["source"]))
            else:
                line.append((' ' * (maxx - ((len(source_msg) + len(user) + (5 + len(cout))))), identicurse.colour_fields["none"]))
                line.append(source_msg, identicurse.colour_fields["source"])

            self.buffer.append(line)

            try:
                self.buffer.append([(n['text'], identicurse.colour_fields["notice"])])
            except UnicodeDecodeError:
                self.buffer.append([("Caution: Terminal too shit to display this notice.", identicurse.colour_fields["none"])])

            if not self.compact_style:
                line = []
                line.append((" " * (maxx - (len(time_msg) + 2)), identicurse.colour_fields["time"]))
                line.append((time_msg, identicurse.colour_fields["none"]))
                
                self.buffer.append(line)
                self.buffer.append([])

            self.buffer.append([])

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
