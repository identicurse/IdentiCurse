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

import time, datetime

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
