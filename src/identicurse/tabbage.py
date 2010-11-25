#!/usr/bin env python
import os.path
import re
import threading
import datetime, locale
import time_helper
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

        fun = getattr(self.callback_object, self.callback_function)
        fun()

class Tab(object):
    def __init__(self, window):
        self.window = window
        self.buffer = Buffer()
        self.start_line = 0
        self.html_regex = re.compile("<(.|\n)*?>")
        self.page = 1
        
    def prevpage(self):
        self.page -= 1
        if self.page < 1:
            self.page = 1
            return False
        return True
    
    def nextpage(self):
        self.page += 1
        return True
    
    def scrollup(self, n):
        self.start_line -= n
        if self.start_line < 0:
            self.start_line = 0

    def scrolldown(self, n):
        self.start_line += n
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        if self.start_line > len(self.buffer.reflowed(maxx - 2)) - (maxy - 3):
            self.start_line = len(self.buffer.reflowed(maxx - 2)) - (maxy - 3)

    def display(self):
        maxy, maxx = self.window.getmaxyx()[0], self.window.getmaxyx()[1]
        self.window.erase()
        self.window.addstr("\n".join(self.buffer.reflowed(maxx - 2)[self.start_line:maxy - 3 + self.start_line]).encode("utf-8"))
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
    def __init__(self, conn, window, timeline, type_params={}):
        self.conn = conn
        self.timeline = []
        self.timeline_type = timeline
        self.type_params = type_params

        if self.timeline_type == "user":
            self.name = "User (%s)" % self.type_params['screen_name']
        elif self.timeline_type == "tag":
            self.name = "Tag (%s)" % self.type_params['tag']
        elif self.timeline_type == "group":
            self.name = "Group (%s)" % self.type_params['nickname']
        elif self.timeline_type == "search":
            self.name = "Search (%s)" % self.type_params['query']
        elif self.timeline_type == "sentdirect":
            self.name = "Sent Directs"
        else:
            self.name = self.timeline_type.capitalize()

        Tab.__init__(self, window)

    def get_time(self, time):
        timestamp = strptime(time)

    def update(self):
        if self.timeline_type == "home":
            self.timeline = self.conn.statuses_home_timeline(count=25, page=self.page)
        elif self.timeline_type == "mentions":
            self.timeline  = self.conn.statuses_mentions(count=25, page=self.page)
        elif self.timeline_type == "direct":
            self.timeline = self.conn.direct_messages(count=25, page=self.page)
        elif self.timeline_type == "public":
            self.timeline = self.conn.statuses_public_timeline()
        elif self.timeline_type == "user":
            self.timeline = self.conn.statuses_user_timeline(user_id=self.type_params['user_id'], screen_name=self.type_params['screen_name'], count=25, page=self.page)
        elif self.timeline_type == "group":
            self.timeline = self.conn.statusnet_groups_timeline(group_id=self.type_params['group_id'], nickname=self.type_params['nickname'], count=25, page=self.page)
        elif self.timeline_type == "tag":
            self.timeline = self.conn.statusnet_tags_timeline(tag=self.type_params['tag'], count=25, page=self.page)
        elif self.timeline_type == "sentdirect":
            self.timeline = self.conn.direct_messages_sent(count=25, page=self.page)
        elif self.timeline_type == "favourites":
            self.timeline = self.conn.favorites(page=self.page)
        elif self.timeline_type == "search":
            self.timeline = self.conn.search(self.type_params['query'], page=self.page, standardise=True)

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
            time_msg = time_helper.time_since(datetime_notice)
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1
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

class Context(Tab):
    def __init__(self, conn, window, notice_id):
        self.conn = conn
        self.notice = notice_id
        self.timeline = []

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
            time_msg = time_helper.time_since(datetime_notice)
            
            self.buffer.append(str(c))
            y = len(self.buffer) - 1
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
        self.buffer.append("@" + self.profile['screen_name'].encode("utf-8") + "'s Profile")
        self.buffer.append("")
        self.buffer.append("")

        if self.profile['name']:
            self.buffer.append("Real Name: " + self.profile['name'])
            self.buffer.append("")
       
        if self.profile['description']:
            self.buffer.append("Bio: " + self.profile['description'])
        if self.profile['location']:
            self.buffer.append("Location: " + str(self.profile['location']))
        if self.profile['url']:
            self.buffer.append("URL: " + str(self.profile['url']))
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

        if self.profile['statuses_count']:
            self.buffer.append("Notices: " + str(self.profile['statuses_count']))
        if self.profile['favourites_count']:
            self.buffer.append("Favourites: " + str(self.profile['favourites_count']))
