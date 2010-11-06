#!/usr/bin/env python
import time, datetime

def time_since(datetime_then):
#    utc = TZ_UTC()
    time_diff_raw = datetime.datetime.now() - datetime_then
    days_since = time_diff_raw.days
    seconds_since = time_diff_raw.seconds
    time_diff = {}

    time_diff['days'] = int(round(days_since))

    time_diff['hours'] = int(round(seconds_since / (60 * 60)))
    seconds_since -= time_diff['hours'] * (60 * 60)

    time_diff['minutes'] = int(round(seconds_since / 60))
    seconds_since -= time_diff['minutes'] * 60
    
    time_diff['seconds'] = int(round(seconds_since))
    
    timestr = ""
    
    for unit in ['days', 'hours', 'minutes', 'seconds']:
        if time_diff[unit] > 1:
            timestr += "%d %s " % (time_diff[unit], unit)
        elif time_diff[unit] == 1:
            timestr += "%d %s " % (time_diff[unit], unit[:-1])
    
    timestr += "ago"

    return timestr

