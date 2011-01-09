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

import os.path, re, sys, threading, datetime, locale, helpers, curses, random, identicurse
DATETIME_FORMAT = "%a %b %d %H:%M:%S +0000 %Y"

class Buffer(list):
    def __init__(self):
        list.__init__(self)

    def append(self, item):
        clean_item = []
        for block in item:
            clean_blocks = []
            try:
                if "\n" in block[0]:
                    for sub_block in block[0].split("\n"):
                        clean_blocks.append((sub_block, block[1]))
                else:
                    clean_blocks.append(block)
                for block in clean_blocks: 
                    if "\t" in block[0]:
                        block = ("    ".join(block[0].split("\t")), block[1])
                    clean_text = ""
                    for char in block[0]:
                        try:
                            clean_text += char.encode(sys.getfilesystemencoding())
                        except UnicodeEncodeError:
                            clean_text += "?"
                    clean_block = (clean_text, block[1])
                    clean_item.append(clean_block)
            except TypeError:
                raise Exception(item)
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
                    split_point = helpers.find_split_point(block[0], len(block[0]) - overlong_by + 1)
                    reflowed_buffer[-1].append((block[0][:split_point], block[1]))
                    reflowed_buffer.append([])
                    reflowed_buffer[-1].append((block[0][split_point:], block[1]))
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
        self.search_highlight_line = -1
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

    def scrollto(self, n, force_top=True):  # attempt to get line number n onto the screen (to the top if force_top==True) - this is less clean than the relative scrolls, so don't call it unless you *need* to go to a specific line.
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if (n >= self.start_line) and (n < (maxy - 3 + self.start_line)) and not force_top:  # if the line is already visible and force_top==False, bail out
            return
        if (n > self.start_line) and (n > len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)) and force_top:
            self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)
        elif n < self.start_line or force_top:
            self.start_line = n
        else:
            self.start_line = n - (maxy - 4)


    def scrolltodent(self, n, smooth_scroll=False):
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
                    if smooth_scroll and (dent_line >= (maxy - 3 + self.start_line)):
                        buffer_cache = self.buffer.reflowed(maxx - 2)
                        while True:
                            if dent_line == len(buffer_cache) - 1:
                                break
                            line_length = 0
                            for block in buffer_cache[dent_line+1]:
                                line_length += len(block[0])
                            if line_length == 0:
                                break
                            dent_line += 1
                        self.scrollto(dent_line, force_top=False)
                    elif (dent_line >= (maxy - 3 + self.start_line)) or (dent_line < self.start_line):
                        self.scrollto(dent_line, force_top=True)
                    return
            dent_line += 1

    def display(self):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        self.window.erase()

        buffer = self.buffer.reflowed(maxx - 2)
        line_num = self.start_line
        for line in buffer[self.start_line:maxy - 3 + self.start_line]:
            remaining_line_length = maxx - 2
            for (part, attr) in line:
                if line_num == self.search_highlight_line:
                    remaining_line_length -= len(part)
                    self.window.addstr(part, curses.color_pair(identicurse.colour_fields['search_highlight']))
                else:
                    self.window.addstr(part, curses.color_pair(attr))
            if line_num == self.search_highlight_line:
                self.window.addstr(" "*remaining_line_length, curses.color_pair(identicurse.colour_fields['search_highlight']))
            self.window.addstr("\n")
            line_num += 1
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
        for l in open(self.path, 'r').readlines():
            self.buffer.append([(l, identicurse.colour_fields['none'])])

class Timeline(Tab):
    def __init__(self, conn, window, timeline, type_params={}, notice_limit=25, filters=[], compact_style=False, user_rainbow=False, tag_rainbow=False, group_rainbow=False, expand_remote=False):
        self.conn = conn
        self.timeline = []
        self.raw_mentions_timeline = []
        self.user_cache = {}
        self.tag_cache = {}
        self.group_cache = {}
        self.timeline_type = timeline
        self.type_params = type_params
        self.notice_limit = notice_limit
        self.filters = filters
        self.compact_style = compact_style
        self.user_rainbow = user_rainbow
        self.tag_rainbow = tag_rainbow
        self.group_rainbow = group_rainbow
        self.expand_remote = expand_remote
        self.highlight_regex = re.compile(r'([@!#]\w+)')
        if self.expand_remote:
            self.title_regex = re.compile("\<title\>(.*)\<\/title\>")
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
            if raw_timeline != self.raw_timeline:
                curses.flash()
            self.raw_mentions_timeline = raw_timeline
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
                if self.expand_remote and "attachments" in notice:
                    import urllib2
                    for attachment in notice['attachments']:
                        if attachment['mimetype'] != "text/html":
                            continue
                        req = urllib2.Request(attachment['url'])
                        page = urllib2.urlopen(req).read()
                        notice['text'] = self.title_regex.findall(page)[0]
                        break
                self.timeline.append(notice)

        if self.page > 1:
            self.name = self.basename + "+%d" % (self.page - 1)
        else:
            self.name = self.basename

        self.search_highlight_line = -1

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
                time_msg = helpers.format_time(helpers.time_since(datetime_notice), short_form=True)
            else:
                time_msg = helpers.format_time(helpers.time_since(datetime_notice))

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
                line.append((source_msg, identicurse.colour_fields["source"]))

            self.buffer.append(line)

            try:
                line = []

                notice_parts = self.highlight_regex.split(n['text'])
                for part in notice_parts:
                    part_list = list(part)
                    if len(part_list) > 0:
                        if part_list[0] in ['@', '!', '#']:
                            highlight_part = str("".join(part_list[1:]))
                            if part_list[0] == '@':
                                if self.user_rainbow:
                                    if not highlight_part in self.user_cache:
                                        self.user_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.user_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['username']))
                            elif part_list[0] == '!':
                                if self.group_rainbow:
                                    if not highlight_part in self.group_cache:
                                        self.group_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.group_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['group']))
                            elif part_list[0] == '#':
                                if self.tag_rainbow:
                                    if not highlight_part in self.tag_cache:
                                        self.tag_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.tag_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['tag']))
                        else:
                            line.append((part, identicurse.colour_fields["notice"]))

                self.buffer.append(line)

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
    def __init__(self, conn, window, notice_id, compact_style=False, user_rainbow=False, tag_rainbow=False, group_rainbow=False, expand_remote=False):
        self.conn = conn
        self.notice = notice_id
        self.timeline = []
        self.compact_style = compact_style
        self.user_rainbow = user_rainbow
        self.tag_rainbow = tag_rainbow
        self.group_rainbow = group_rainbow
        self.user_cache = {}
        self.tag_cache = {}
        self.group_cache = {}
        self.expand_remote = expand_remote
        self.highlight_regex = re.compile(r'([@!#]\w+)')
        if self.expand_remote:
            self.title_regex = re.compile("\<title\>(.*)\<\/title\>")
        self.chosen_one = 0

        self.name = "Context"

        Tab.__init__(self, window)

    def update(self):
        self.timeline = []
        next_id = self.notice

        while next_id is not None:
            notice = self.conn.statuses_show(id=next_id)
            if self.expand_remote and "attachments" in notice:
                import urllib2
                for attachment in notice['attachments']:
                    if attachment['mimetype'] != "text/html":
                        continue
                    req = urllib2.Request(attachment['url'])
                    page = urllib2.urlopen(req).read()
                    notice['text'] = self.title_regex.findall(page)[0]
                    break
            self.timeline.append(notice)
            if "retweeted_status" in self.timeline[-1]:
                next_id = self.timeline[-1]['retweeted_status']['id']
            else:
                next_id = self.timeline[-1]['in_reply_to_status_id']

        self.search_highlight_line = -1

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
                time_msg = helpers.format_time(helpers.time_since(datetime_notice), short_form=True)
            else:
                time_msg = helpers.format_time(helpers.time_since(datetime_notice))
            
            if not user in self.user_cache:
                self.user_cache[user] = random.choice(identicurse.base_colours.items())[1]

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
                line.append((source_msg, identicurse.colour_fields["source"]))

            self.buffer.append(line)

            try:
                line = []

                notice_parts = self.highlight_regex.split(n['text'])
                wtf = False
                for part in notice_parts:
                    part_list = list(part)
                    if len(part_list) > 0:
                        if part_list[0] in ['@', '!', '#']:
                            highlight_part = str("".join(part_list[1:]))
                            if part_list[0] == '@':
                                if self.user_rainbow:
                                    if not highlight_part in self.user_cache:
                                        self.user_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.user_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['username']))
                            elif part_list[0] == '!':
                                if self.group_rainbow:
                                    if not highlight_part in self.group_cache:
                                        self.group_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.group_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['group']))
                            elif part_list[0] == '#':
                                if self.tag_rainbow:
                                    if not highlight_part in self.tag_cache:
                                        self.tag_cache[highlight_part] = random.choice(identicurse.base_colours.items())[1]
                                    line.append((part, self.tag_cache[highlight_part]))
                                else:
                                    line.append((part, identicurse.colour_fields['tag']))
                        else:
                            line.append((part, identicurse.colour_fields["notice"]))

                self.buffer.append(line)

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

        self.fields = [
                # display name,           internal field name,  skip a line after this field?
                ("Real Name",             "name",               True),
                ("Bio",                   "description",        False),
                ("Location",              "location",           False),
                ("URL",                   "url",                False),
                ("User ID",               "id",                 False),
                ("Joined at",             "created_at",         True),
                ("Followed by",           "followers_count",    False),
                ("Following",             "friends_count",      False),
                ("Followed by you",       "following",          True),
                ("Favourites",            "favourites_count",   False),
                ("Notices",               "statuses_count",     False),
                ("Average daily notices", "notices_per_day",    True)
                ]

        Tab.__init__(self, window)

    def update(self):
        self.profile = self.conn.users_show(screen_name=self.id)

        # numerical fields, convert them to strings to make the buffer code more clean
        for field in ['id', 'created_at', 'followers_count', 'friends_count', 'favourites_count', 'statuses_count']:
            self.profile[field] = str(self.profile[field])

        # special handling for following
        if self.profile['following']:
            self.profile['following'] = "Yes"
        else:
            self.profile['following'] = "No"

        # create this field specially
        locale.setlocale(locale.LC_TIME, 'C')  # hacky fix because statusnet uses english timestrings regardless of locale
        datetime_joined = datetime.datetime.strptime(self.profile['created_at'], DATETIME_FORMAT)
        locale.setlocale(locale.LC_TIME, '') # other half of the hacky fix
        days_since_join = helpers.single_unit(helpers.time_since(datetime_joined), "days")['days']
        self.profile['notices_per_day'] = "%0.2f" % (float(self.profile['statuses_count']) / days_since_join)

        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()

        self.buffer.append([("@" + self.profile['screen_name'] + "'s Profile", identicurse.colour_fields['profile_title'])])
        self.buffer.append([("", identicurse.colour_fields['none'])])

        for field in self.fields:
            if self.profile[field[1]] is not None:
                line = []

                line.append((field[0] + ":", identicurse.colour_fields['profile_fields']))
                line.append((" ", identicurse.colour_fields['none']))

                line.append((self.profile[field[1]], identicurse.colour_fields['profile_values']))

                self.buffer.append(line)

            if field[2]:
                self.buffer.append([("", identicurse.colour_fields['none'])])
