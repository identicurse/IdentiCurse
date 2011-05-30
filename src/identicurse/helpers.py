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

import time, datetime, htmlentitydefs, re, urllib, urllib2, locale, os, platform, sys, string
DATETIME_FORMAT = "%a %b %d %H:%M:%S +0000 %Y"
offset_regex = re.compile("[+-][0-9]{4}")
base_url_regex = re.compile("(http(s|)://.+?)/.*")
title_regex = re.compile("\<title\>(.*)\<\/title\>")
ur1_regex = re.compile("Your ur1 is: <a.+?>(http://ur1\.ca/[0-9A-Za-z]+)")
url_regex = re.compile("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

def notice_datetime(notice):
    locale.setlocale(locale.LC_TIME, 'C')  # hacky fix because statusnet uses english timestrings regardless of locale
    created_at_no_offset = offset_regex.sub("+0000", notice['created_at'])
    attempts = 10
    while attempts > 0:
        attempts -= 1
        try:
            normalised_datetime = datetime.datetime.strptime(created_at_no_offset, DATETIME_FORMAT) + utc_offset(notice['created_at'])
            break
        except ValueError:  # something else changed the locale, and Python threw a hissy fit
            pass
    locale.setlocale(locale.LC_TIME, '') # other half of the hacky fix
    return normalised_datetime

def time_since(datetime_then):
    if datetime_then > datetime.datetime.utcnow():
        return {'days':0, 'hours':0, 'minutes':0, 'seconds':0}
    time_diff_raw = datetime.datetime.utcnow() - datetime_then
    days_since = time_diff_raw.days
    seconds_since = time_diff_raw.seconds
    time_diff = {}

    time_diff['days'] = int(round(days_since))

    time_diff['hours'] = int(round(seconds_since / (60 * 60)))
    seconds_since -= time_diff['hours'] * (60 * 60)

    time_diff['minutes'] = int(round(seconds_since / 60))
    seconds_since -= time_diff['minutes'] * 60
    
    time_diff['seconds'] = int(round(seconds_since))

    return time_diff

def format_time(time_dict, floating=False, short_form=False):
    timestr = ""
    if short_form:
        formatstr = "%d%s "
    else:
        if floating:
            formatstr = "%0.1f %s "
        else:
            formatstr = "%d %s "

    if short_form:
        if time_dict['days'] > 0:
            if time_dict['hours'] >= 12:
                time_dict['days'] += 1
            if (time_dict['hours'] != 0) or (time_dict['minutes'] != 0) or (time_dict['seconds'] != 0):
                # timestr = "~"
                time_dict['hours'], time_dict['minutes'], time_dict['seconds'] = 0, 0, 0
        elif time_dict['hours'] > 0:
            if time_dict['minutes'] >= 30:
                time_dict['hours'] += 1
            if (time_dict['minutes'] != 0) or (time_dict['seconds'] != 0):
                # timestr = "~"
                time_dict['minutes'], time_dict['seconds'] = 0, 0
        elif time_dict['minutes'] > 0:
            if time_dict['seconds'] >= 30:
                time_dict['minutes'] += 1
            if time_dict['seconds'] != 0:
                # timestr = "~"
                time_dict['seconds'] = 0
    
    for unit in ['days', 'hours', 'minutes', 'seconds']:
        if short_form:
            if time_dict[unit] > 0:
                timestr += formatstr % (time_dict[unit], unit[0])
        else:
            if time_dict[unit] > 1:
                timestr += formatstr % (time_dict[unit], unit)
            elif time_dict[unit] == 1:
                timestr += formatstr % (time_dict[unit], unit[:-1])
    
    if timestr == "":
        timestr = "Now"
    else:
        timestr += "ago"

    return timestr

def single_unit(time_dict, unit):
    total_seconds = float(time_dict['seconds'])
    total_seconds += (time_dict['minutes'] * 60)
    total_seconds += (time_dict['hours'] * (60 * 60))
    total_seconds += (time_dict['days'] * (60 * 60 * 24))

    time_dict = {'days':0, 'hours':0, 'minutes':0, 'seconds':0}
    if unit == "seconds":
        time_dict['seconds'] = total_seconds
    elif unit == "minutes":
        time_dict['minutes'] = (total_seconds / 60)
    elif unit == "hours":
        time_dict['hours'] = (total_seconds / (60 * 60))
    elif unit == "days":
        time_dict['days'] = (total_seconds / (60 * 60 * 24))
    return time_dict

def utc_offset(time_string):
    offset = offset_regex.findall(time_string)[0]
    offset_hours = int(offset[1:3])
    offset_minutes = int(offset[3:])
    return datetime.timedelta(hours=offset_hours,minutes=offset_minutes)

def find_split_point(text, width):
    split_point = width - 1
    while True:
        if split_point == 0:  # no smart split point was found, split unsmartly
            split_point = width - 1
            break
        elif split_point < 0:
            split_point = 0
            break
        if text[split_point-1] == " ":
            break
        else:
            split_point -= 1
    return split_point

def html_unescape_block(block):
    block_text = block.group(0)
    block_codepoint = None

    if block_text[:2] == "&#":  # codepoint
        try:
            if block_text[2] == "x":  # hexadecimal codepoint
                block_codepoint = int(block_text[3:-1], 16)
            else:  # decimal codepoint
                block_codepoint = int(block_text[2:-1])
        except ValueError:  # codepoint was mangled/invalid, don't bother trying to interpret it
            pass
    else:  # named character
        try:
            block_codepoint = htmlentitydefs.name2codepoint[block_text[1:-1]]
        except KeyError:  # name was invalid, don't try to interpret
            pass

    if block_codepoint is not None:
        return unichr(block_codepoint)
    else:
        return block_text

def html_unescape_string(escaped_string):
    return re.sub("&#?\w+;", html_unescape_block, escaped_string)

def find_longest_common_start(words):
    if len(words) == 0:
        return ""
    last_match = ""
    for length in xrange(len(words[0]) + 1):
        match_string = words[0][:length]
        match = True
        for word in words:
            if word[:length] != match_string:
                match = False
        if not match:
            break
        last_match = match_string
    return last_match

def find_fuzzy_matches(fragment, words):
    if len(fragment) == 0:
        return []
    matches = []
    for word in words:
        fragment_index = 0
        for char in word:
            if char == fragment[fragment_index]:
                fragment_index += 1
            if fragment_index == len(fragment):  # all chars existed in order, this is a fuzzy match
                matches.append(word)
                break
    return matches

def ur1ca_shorten(longurl):
    request = urllib2.Request("http://ur1.ca/", urllib.urlencode({'longurl':longurl}))
    response = urllib2.urlopen(request)
    page = response.read()
    results = ur1_regex.findall(page)
    if len(results) > 0:
        return results[0]
    else:  # something went wrong, return the original url
        return longurl

def set_terminal_title(title_text):
    if platform.system() != "Windows":
        sys.stdout.write("\x1b]0;" + title_text + "\x07")  # set the title the unix-y way
    else:
        os.system("title " + title_text)  # do it the windows-y way

def split_entities(raw_notice_text):
    entities = [{"text":"", "type":"plaintext"}]
    raw_notice_text = " " + raw_notice_text + " "
    char_index = 0
    while char_index < len(raw_notice_text):
        if entities[-1]['type'] != "plaintext" and not raw_notice_text[char_index].isalnum() and not raw_notice_text[char_index] in [".", "_", "-"]:
            next_entity_text = ""
            for i in xrange(len(entities[-1]['text'])):
                if len(entities[-1]['text']) > 1 and entities[-1]['text'][-1] in [".", "-"]:
                    next_entity_text += entities[-1]['text'][-1]
                    entities[-1]['text'] = entities[-1]['text'][:-1]
                else:
                    break
            entities.append ({"text":next_entity_text, "type":"plaintext"})
        if (raw_notice_text[char_index] in string.whitespace or raw_notice_text[char_index] in string.punctuation) and char_index < (len(raw_notice_text) - 2):
            entities[-1]['text'] += raw_notice_text[char_index]
            char_index += 1
            if raw_notice_text[char_index] in ["@", "!", "#"] and (raw_notice_text[char_index+1].isalnum() or (raw_notice_text[char_index+1] in [".", "_", "-"])):
                if raw_notice_text[char_index] == "@":
                    entities.append({"text":"@", "type":"user"})
                elif raw_notice_text[char_index] == "!":
                    entities.append({"text":"!", "type":"group"})
                elif raw_notice_text[char_index] == "#":
                    entities.append({"text":"#", "type":"tag"})
                char_index += 1
        else:
            entities[-1]['text'] += raw_notice_text[char_index]
            char_index += 1
    # strip the extra space that was prepended
    if entities[0]['text'] == " ":
        entities = entities[1:]
    else:
        entities[0]['text'] = entities[0]['text'][1:]
    # and the one that was appended
    if entities[-1]['text'] == " ":
        entities = entities[:-1]
    else:
        entities[-1]['text'] = entities[-1]['text'][:-1]
    return entities
