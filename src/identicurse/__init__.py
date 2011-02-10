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

from identicurse import IdentiCurse
from optparse import OptionParser
import random, os

preset_slogans = [
            "100% hippy-approved",
            "powered by hatred",
            "we don't get OAuth either",
            "don't drink and dent",
            "@psquid can't spell hippy",
            "Stupid sexy Flanders",
            "curry in the i-webs",
            "Got GNOME git commit access",
            "YOUR SOUL TO THE HOMOSEXUAL AGENDA",
            "Bullshit Bingo",
            "trying to do teh frees",
            "coming and coming and coming and coming",
            "Do you store your passwords in the back yard?",
            "Let's neuter this bullshit!",
            "it's probably just recycled bullshit.",
            "I'm on a rampage and kill everyone.",
            "a Tragedie in three parts.",
            "#metamicroblogging",
            "#metametamicroblogging",
            "EXCEPT IN NEBRASKA",
            "ATTENTION SNOW: GTFO ITS TOO WARM FOR YOU!",
            "eating paracetamol sandwiches.",
            "Do not operate heavy machinery while using IdentiCurse.",
            "39% the same as bathing in fine grape juice.",
            "DOT MATRIX WITH STEREO SOUND",
            "oh god how did this get here I am not good with computer",
            "Pregnant women and those with heart conditions are advised against using this software.",
          ]

def main():
    """
    Innit.
    """
    parser = OptionParser()
    parser.add_option("-c", "--config",
            help="specify an alternative config file to use",
            action="store", type="string", dest="config_filename", metavar="FILE")
    parser.add_option("-s", "--slogans",
            help="specify an alternative slogans file to use",
            action="store", type="string", dest="slogans_filename", metavar="FILE")
    parser.add_option("--colour-check",
            help="check if system curses library supports colours, and how many",
            action="store_true", dest="colour_check")
    (options, args) = parser.parse_args()

    if (options.colour_check is not None) and (options.colour_check == True):
        colour_check()
        return

    additional_config = {}

    if options.slogans_filename is not None:
        user_slogans_file = os.path.expanduser(options.slogans_filename)
    else:
        user_slogans_file = os.path.join(os.path.expanduser("~"), ".identicurse_slogans")
    
    if options.config_filename is not None:
        additional_config['config_filename'] = options.config_filename

    try:
        user_slogans_raw = open(user_slogans_file).read()
        user_slogans = [slogan for slogan in user_slogans_raw.split("\n") if slogan.strip() != ""]
        slogans = user_slogans
    except:
        slogans = preset_slogans
    print "Welcome to IdentiCurse 0.6.4 (Fishguard) - %s" % (random.choice(slogans))
    IdentiCurse(additional_config)

def colour_check():
    import curses
    curses.initscr()
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        msg = "Your system's curses library supports %d colours." % (curses.COLORS)
    else:
        msg = "Your system's curses library does not support colours."
    curses.endwin()
    print msg

if __name__ == '__main__':
    main()
