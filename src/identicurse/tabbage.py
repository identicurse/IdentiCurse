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

from helpers import DATETIME_FORMAT
import os.path, re, sys, threading, datetime, locale, curses, random, httplib
import identicurse, config, helpers
from operator import itemgetter
from statusnet import StatusNetError

class Buffer(list):
    def __init__(self):
        list.__init__(self)

    def append(self, item):
        clean_item = []
        for block in item:
            clean_blocks = []
            try:
                if "\n" in block[0]:
                    clean_blocks.append((block[0].split("\n")[0].replace("\r", ""), block[1]))
                    for sub_block in block[0].split("\n")[1:]:
                        clean_blocks.append((" "+sub_block.replace("\r", ""), block[1]))
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

        for raw_line in self:
            reflowed_buffer.append([])
            line_length = 0
            line = raw_line[:]
            line.reverse()  # reverse the line so we can use it as a stack
            while len(line) > 0:
                block = line.pop()
                try:  # attempt to consider possibly different unicode length vs. ascii length
                    block_len = len(block[0].encode(sys.getfilesystemencoding()))
                except:
                    block_len = len(block)
                if (block_len + line_length) > width:
                    split_point = helpers.find_split_point(block[0], width - line_length)
                    reflowed_buffer[-1].append((block[0][:split_point], block[1]))  # add the first half of the block as usual
                    reflowed_buffer.append([])
                    line.append((block[0][split_point:], block[1]))  # put the rest of the block back on the stack
                    line_length = 0
                else:
                    reflowed_buffer[-1].append(block)
                    line_length += block_len

        return reflowed_buffer

class TabUpdater(threading.Thread):
    def __init__(self, tabs, callback_object, callback_function):
        threading.Thread.__init__(self)
        self.daemon = True
        self.tabs = tabs
        self.callback_object = callback_object
        self.callback_function = callback_function

    def run (self):
        config.session_store.update_error=None
        for tab in self.tabs:
            try:
                self.callback_object.status_bar.update("Updating '%s'..." % (tab.name))
                tab.update()
            except StatusNetError, e:
                config.session_store.update_error="Status.Net error %d in '%s': %s" % (e.errcode, tab.name, e.details)
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
        self.paused = False
        
    def prevpage(self, n=1):
        if hasattr(self, "timeline"):
            if n > 0:
                self.page -= n
                if self.page < 1:
                    self.page = 1
                    return False
                self.scrolldown(0)  # scroll to the end of the newer page, so the dent immediately after the start of the last page can be seen
                self.chosen_one = len(self.timeline) - 1
            else:
                if self.page == 1:
                    return False
                else:
                    self.page = 1
                    self.scrollup(0)
                    self.chosen_one = 0
            return True
        else:
            return False
    
    def nextpage(self):
        if hasattr(self, "timeline"):
            self.page += 1
            self.scrollup(0)  # as in prevpage, only the other way around
            self.chosen_one = 0
            return True
        else:
            return False
    
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
            try:
                for (part, attr) in line:
                    if attr == identicurse.colour_fields["pause_line"]:  # we want pause lines to fill the width
                        self.window.addstr("-"*(remaining_line_length-1), curses.color_pair(identicurse.colour_fields['pause_line']))
                    if line_num == self.search_highlight_line:
                        remaining_line_length -= len(part)
                        self.window.addstr(part, curses.color_pair(identicurse.colour_fields['search_highlight']))
                    else:
                        self.window.addstr(part, curses.color_pair(attr))
                if line_num == self.search_highlight_line:
                    self.window.addstr(" "*remaining_line_length, curses.color_pair(identicurse.colour_fields['search_highlight']))
                if line_num <= (maxy - 3 + self.start_line):
                        self.window.addstr("\n")
            except:  # if we somehow already hit the bottom (maybe there were weird chars?)
                pass  # just ignore it and move on
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
    def __init__(self, conn, window, timeline, type_params={}):
        self.conn = conn
        self.timeline = []
        self.prev_page = -1
        if not hasattr(config.session_store, 'user_cache'):
            config.session_store.user_cache = {}
        if not hasattr(config.session_store, 'tag_cache'):
            config.session_store.tag_cache = {}
        if not hasattr(config.session_store, 'group_cache'):
            config.session_store.group_cache = {}
        self.timeline_type = timeline
        self.type_params = type_params
        self.chosen_one = 0

        if self.timeline_type == "user":
            self.basename = "@%s" % self.type_params['screen_name']
        elif self.timeline_type == "tag":
            self.basename = "#%s" % self.type_params['tag']
        elif self.timeline_type == "group":
            self.basename = "!%s" % self.type_params['nickname']
        elif self.timeline_type == "search":
            self.basename = "Search: '%s'" % self.type_params['query']
        elif self.timeline_type == "sentdirect":
            self.basename = "Sent Directs"
        else:
            self.basename = self.timeline_type.capitalize()
        self.name = self.basename
        
        Tab.__init__(self, window)

    def update_name(self):
        if self.page > 1:
            self.name = self.basename + "+%d" % (self.page - 1)
        else:
            self.name = self.basename

        if self.paused:
            self.name = self.name + " (paused)"

    def update(self):
        self.update_name()

        if self.paused:
            self.update_buffer()
            return

        get_count = config.config['notice_limit']

        if self.prev_page != self.page:
            self.timeline = []

        last_id = 0
        if len(self.timeline) > 0:
            for notice in self.timeline:
                if notice["ic__from_web"]:  # don't consider inserted posts latest
                    last_id = notice['id']
                    break

        if self.timeline_type == "home":
            raw_timeline = self.conn.statuses_home_timeline(count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "mentions":
            raw_timeline = self.conn.statuses_mentions(count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "direct":
            raw_timeline = self.conn.direct_messages(count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "user":
            raw_timeline = self.conn.statuses_user_timeline(user_id=self.type_params['user_id'], screen_name=self.type_params['screen_name'], count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "group":
            raw_timeline = self.conn.statusnet_groups_timeline(group_id=self.type_params['group_id'], nickname=self.type_params['nickname'], count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "tag":
            raw_timeline = self.conn.statusnet_tags_timeline(tag=self.type_params['tag'], count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "sentdirect":
            raw_timeline = self.conn.direct_messages_sent(count=get_count, page=self.page, since_id=last_id)
        elif self.timeline_type == "public":
            raw_timeline = self.conn.statuses_public_timeline()
        elif self.timeline_type == "favourites":
            raw_timeline = self.conn.favorites(page=self.page, since_id=last_id)
        elif self.timeline_type == "search":
            raw_timeline = self.conn.search(self.type_params['query'], page=self.page, standardise=True, since_id=last_id)
        elif self.timeline_type == "context":
            raw_timeline = []
            if "conversation_id" in self.type_params:  # try to do it the new way
                raw_timeline = self.conn.statusnet_conversation(self.type_params['conversation_id'], count=get_count, since_id=last_id, page=self.page)
            else:
                if last_id == 0:  # don't run this if we've already filled the timeline
                    next_id = self.type_params['notice_id']
                    while next_id is not None:
                        notice = self.conn.statuses_show(id=next_id)
                        raw_timeline.append(notice)
                        if "retweeted_status" in notice:
                            next_id = notice['retweeted_status']['id']
                        else:
                            next_id = notice['in_reply_to_status_id']

        self.prev_page = self.page

        temp_timeline = []
        old_ids = [n['id'] for n in self.timeline]

        for notice in raw_timeline:
            notice["ic__raw_datetime"] = helpers.normalise_datetime(notice['created_at'])
            notice["ic__from_web"] = True
            passes_filters = True
            if notice['id'] in old_ids:
                passes_filters = False
                continue
            if hasattr(config.session_store, "muted_conversations") and notice['statusnet_conversation_id'] in config.session_store.muted_conversations:
                passes_filters = False
                continue
            if config.config["hide_activities"] and ("source" in notice) and (notice["source"] == "activity"):
                passes_filters = False
                continue
            if config.config["filter_mode"] == "regex":
                for filter_item in config.config['filters']:
                    if filter_item.search(notice['text']) is not None:
                        passes_filters = False
                        break
            else:
                for filter_item in config.config['filters']:
                    if filter_item.lower() in notice['text'].lower():
                        passes_filters = False
                        break
            if passes_filters:
                if (not self.timeline_type in ["direct", "sentdirect"]) and notice["source"] == "ostatus" and config.config['expand_remote'] and "attachments" in notice:
                    import urllib2
                    for attachment in notice['attachments']:
                        if attachment['mimetype'] != "text/html":
                            continue
                        req = urllib2.Request(attachment['url'])
                        try:
                            page = urllib2.urlopen(req).read()
                            try:
                                notice['text'] = helpers.html_unescape_string(helpers.title_regex.findall(page)[0])
                            except IndexError:  # no title could be found
                                pass
                        except:  # link was broken
                            pass
                        break
                temp_timeline.append(notice)

        if self.timeline_type in ["direct", "mentions"]:  # alert on changes to these. maybe config option later?
            if (len(self.timeline) > 0) and (len(temp_timeline) > 0):  # only fire when there's new stuff _and_ we've already got something in the timeline
                if config.config['notify'] == 'flash':
                    curses.flash()
                elif config.config['notify'] == 'beep':
                    curses.beep()

        if len(self.timeline) == 0:
            self.timeline = temp_timeline[:]
        else:
            self.timeline = temp_timeline + self.timeline
            if self.timeline_type != "context" and len(self.timeline) > get_count:  # truncate long timelines
                self.timeline = self.timeline[:get_count]

        self.timeline.sort(key=itemgetter('id'), reverse=True)

        self.search_highlight_line = -1

        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()

        maxx = self.window.getmaxyx()[1]
        c = 1

        longest_metadata_string_len = 0
        for n in self.timeline:
            if "direct" in self.timeline_type:
                user_string = "%s -> %s" % (n["sender"]["screen_name"], n["recipient"]["screen_name"])
                source_msg = ""
            else:
                atless_reply = False
                if "in_reply_to_screen_name" in n and n["in_reply_to_screen_name"] is not None:
                    atless_reply = True
                    for entity in helpers.split_entities(n["text"]):
                        if entity["type"] == "user" and entity["text"][1:].lower() == n["in_reply_to_screen_name"].lower():
                            atless_reply = False
                            break
                if atless_reply:
                    if "user" in n:
                        user_string = "%s" % (n["user"]["screen_name"])
                    else:
                        user_string = "<no username>"
                    user_string += " -> %s" % (n["in_reply_to_screen_name"])
                else:
                    if "user" in n:
                        user_string = "%s" % (n["user"]["screen_name"])
                    else:
                        user_string = ""
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)
            if "in_reply_to_status_id" in n and n["in_reply_to_status_id"] is not None:
                if not config.config["show_source"]:
                    user_string += " +"
                else:
                    source_msg += " [+]"
            if "retweeted_status" in n:
                user_string = "%s [%s's RD]" % (n["retweeted_status"]["user"]["screen_name"], n["user"]["screen_name"])
                if "in_reply_to_status_id" in n["retweeted_status"]:
                    if not config.config["show_source"]:
                        user_string += " +"
                    else:
                        source_msg += " [+]"
            datetime_notice = helpers.normalise_datetime(n["created_at"])
            time_msg = helpers.format_time(helpers.time_since(datetime_notice), short_form=True)
            metadata_string = time_msg + " " + user_string
            if config.config["show_source"]:
                metadata_string += " " + source_msg
            if len(metadata_string) > longest_metadata_string_len:
                longest_metadata_string_len = len(metadata_string)

        for n in self.timeline:
            from_user = None
            to_user = None
            repeating_user = None
            if "direct" in self.timeline_type:
                from_user = n["sender"]["screen_name"]
                to_user = n["recipient"]["screen_name"]
                source_msg = ""
            else:
                if "retweeted_status" in n:
                    repeating_user = n["user"]["screen_name"]
                    n = n["retweeted_status"]
                if "user" in n:
                    from_user = n["user"]["screen_name"]
                else:
                    from_user = "<no username>"
                atless_reply = False
                if "in_reply_to_screen_name" in n and n["in_reply_to_screen_name"] is not None:
                    atless_reply = True
                    for entity in helpers.split_entities(n["text"]):
                        if entity["type"] == "user" and entity["text"][1:].lower() == n["in_reply_to_screen_name"].lower():
                            atless_reply = False
                            break
                if atless_reply:
                    to_user = n["in_reply_to_screen_name"]
                raw_source_msg = "from %s" % (n["source"])
                source_msg = self.html_regex.sub("", raw_source_msg)
                repeat_msg = ""
                if n["in_reply_to_status_id"] is not None:
                    source_msg += " [+]"
            datetime_notice = helpers.normalise_datetime(n["created_at"])

            time_msg = helpers.format_time(helpers.time_since(datetime_notice), short_form=True)

            for user in [user for user in [from_user, to_user, repeating_user] if user is not None]:
                if not user in config.session_store.user_cache:
                    config.session_store.user_cache[user] = random.choice(identicurse.base_colours.items())[1]
           
            if "ic__paused_on" in n and c != 1:
                self.buffer.append([("-", identicurse.colour_fields["pause_line"])])
                self.buffer.append([("", identicurse.colour_fields["none"])])

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

            if config.config['compact_notices']:
                line.append((time_msg, identicurse.colour_fields["time"]))
                line.append((" ", identicurse.colour_fields["none"]))

            if config.config['user_rainbow']:
                line.append((from_user, config.session_store.user_cache[from_user]))
            else:
                line.append((from_user, identicurse.colour_fields["username"]))
            if from_user is not None:
                user_length = len(from_user)
            else:
                user_length = None

            if to_user is not None:
                line.append((" -> ", identicurse.colour_fields["none"]))
                if config.config['user_rainbow']:
                    line.append((to_user, config.session_store.user_cache[to_user]))
                else:
                    line.append((to_user, identicurse.colour_fields["username"]))
                user_length += (len(" -> ") + len(to_user))

            if repeating_user is not None:
                if config.config["compact_notices"]:
                    line.append((" [", identicurse.colour_fields["none"]))
                else:
                    line.append((" [ repeat by ", identicurse.colour_fields["none"]))

                if config.config['user_rainbow']:
                    line.append((repeating_user, config.session_store.user_cache[repeating_user]))
                else:
                    line.append((repeating_user, identicurse.colour_fields["username"]))

                if config.config["compact_notices"]:
                    line.append(("'s RD]", identicurse.colour_fields["none"]))
                    user_length += (len(" [") + len(repeating_user) + len("'s RD]"))
                else:
                    line.append((" ]", identicurse.colour_fields["none"]))
                    user_length += (len(" [ repeat by ") + len(repeating_user) + len(" ]"))

            if not config.config['compact_notices']:
                if config.config["show_source"]:
                    line.append((' ' * (maxx - ((len(source_msg) + len(time_msg) + user_length + (6 + len(cout))))), identicurse.colour_fields["none"]))
                else:
                    line.append((' ' * (maxx - ((len(time_msg) + user_length + (5 + len(cout))))), identicurse.colour_fields["none"]))
                line.append((time_msg, identicurse.colour_fields["time"]))
                if config.config["show_source"]:
                    line.append((' ', identicurse.colour_fields["none"]))
                    line.append((source_msg, identicurse.colour_fields["source"]))
                self.buffer.append(line)
                line = []
            else:
                detail_char = ""
                if (not config.config["show_source"]):
                    if "in_reply_to_status_id" in n and n["in_reply_to_status_id"] is not None:
                        detail_char = "+"
                    elif "retweeted_status" in n:
                        detail_char = "~"
                    line.append((" %s" % (detail_char), identicurse.colour_fields["source"]))
                if config.config["show_source"]:
                        line.append((" " + source_msg, identicurse.colour_fields["source"]))
                        line.append((" "*((longest_metadata_string_len - (user_length + len(time_msg) + len(source_msg) + 2))), identicurse.colour_fields["none"]))
                else:
                    if detail_char == "":
                        line.append((" ", identicurse.colour_fields["none"]))
                    line.append((" "*((longest_metadata_string_len - (user_length + len(time_msg) + 1))), identicurse.colour_fields["none"]))
                line.append((" | ", identicurse.colour_fields["none"]))

            try:
                notice_entities = helpers.split_entities(n['text'])
                for entity in notice_entities:
                    if len(entity['text']) > 0:
                        if entity['type'] in ['user', 'group', 'tag']:
                            entity_text_no_symbol = entity['text'][1:]
                            cache = getattr(config.session_store, '%s_cache' % (entity['type']))
                            if not entity_text_no_symbol in cache:
                                cache[entity_text_no_symbol] = random.choice(identicurse.base_colours.items())[1]
                            if config.config['%s_rainbow' % (entity['type'])]:
                                line.append((entity['text'], cache[entity_text_no_symbol]))
                            else:
                                if entity['type'] == "user":
                                    line.append((entity['text'], identicurse.colour_fields["username"]))
                                else:
                                    line.append((entity['text'], identicurse.colour_fields[entity['type']]))
                        else:
                            line.append((entity['text'], identicurse.colour_fields["notice"]))

                self.buffer.append(line)

            except UnicodeDecodeError:
                self.buffer.append([("Caution: Terminal too shit to display this notice.", identicurse.colour_fields["warning"])])

            if config.config["show_notice_links"]:
                line = []
                base_url = helpers.base_url_regex.findall(self.conn.api_path)[0][0]
                if self.timeline_type in ["direct", "sentdirect"]:
                    notice_link = "%s/message/%s" % (base_url, str(n["id"]))
                else:
                    notice_link = "%s/notice/%s" % (base_url, str(n["id"]))
                line.append(("<%s>" % (notice_link), identicurse.colour_fields["notice_link"]))
                self.buffer.append(line)

            if not config.config['compact_notices']:
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
        try:
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
            datetime_joined = helpers.normalise_datetime(self.profile['created_at'])
            days_since_join = helpers.single_unit(helpers.time_since(datetime_joined), "days")['days']
            self.profile['notices_per_day'] = "%0.2f" % (float(self.profile['statuses_count']) / days_since_join)

        except StatusNetError, e:
            if e.errcode == 404:
                self.profile = None

        self.update_buffer()

    def update_buffer(self):
        self.buffer.clear()

        if self.profile is not None:
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
        else:
            self.buffer.append([("There is no user called @%s on this instance." % (self.id), identicurse.colour_fields['none'])])
