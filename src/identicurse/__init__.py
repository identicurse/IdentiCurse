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
"""
Initial module for IdentiCurse. Parses options and displays slogan,
then hands off control to the main identicurse.py module.
"""

from identicurse import IdentiCurse
from optparse import OptionParser
import random, os

PRESET_SLOGANS = [
    "100% hippy-approved",
    "powered by hatred",
    "we get OAuth now",
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
    "44% the same as bathing in fine grape juice.",
    "DOT MATRIX WITH STEREO SOUND",
    "oh god how did this get here I am not good with computer",
    "Pregnant women and those with heart conditions are advised against using this software.",
    "because some vpn won't run with the cool friends",
    "Making \"git pull\" fun again, since 2010.",
    "like a compact disc to the head!",
    "along with his mechanical ass-kicking leg.",
    "TIME FOR GROUP HUG.",
    "GLORIOUS VICTORY",
    "the sock ruse was a... DISTACTION",
    "wigeons have my car keys.",
    "life is like a zombie in my head.",
    "head to the nearest ENTRANCE and immediately call YOUR MUTANT FIRE DANCING MOON POSSE",
    "it's got what dents crave.",
    "it has lightsabers.",
    "enemy of #scannability.",
    "T-rex rules the school.",
    "GET BLUE SPHERES",
    "not affiliated with @sandersch's nipple.",
    "we're sitti. D next to toy fish",
    ]

def main():
    """
    Innit.
    """
    parser = OptionParser()
    parser.add_option("-c", "--config",
        help="specify an alternative config dir to use", action="store",
        type="string", dest="config_dirname", metavar="FILE")
    parser.add_option("-s", "--slogans",
        help="specify an alternative slogans file to use", action="store",
        type="string", dest="slogans_filename", metavar="FILE")
    parser.add_option("--colour-check",
        help="check if colour support is available, and if so, how many colours",
        action="store_true", dest="colour_check")
    options = parser.parse_args()[0]

    if (options.colour_check is not None) and (options.colour_check == True):
        colour_check()
        return

    additional_config = {}

    if options.slogans_filename is not None:
        user_slogans_file = os.path.expanduser(options.slogans_filename)
    else:
        user_slogans_file = os.path.join(os.path.expanduser("~"),
                                             ".identicurse_slogans")
    
    if options.config_dirname is not None:
        additional_config['config_dirname'] = options.config_dirname

    try:
        user_slogans_raw = open(user_slogans_file).read()
        user_slogans = [slogan for slogan in user_slogans_raw.split("\n")
                                                    if slogan.strip() != ""]
        slogans = user_slogans
    except IOError:
        slogans = PRESET_SLOGANS
    print "Welcome to IdentiCurse 0.8.1 (Holyhead) - %s" % (random.choice(slogans))
    IdentiCurse(additional_config)

def colour_check():
    """
    Display brief message informing user how many colours their system's
    curses library reports as available.
    """
    import curses
    curses.initscr()
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        msg = "System curses library reports that in your current system state, it supports %d colours. For many terminals, adding \"export TERM=xterm-256color\" to your startup scripts will make far more colours available to curses." % (curses.COLORS)
    else:
        msg = "System curses library reports that (at least in your current system state) colour support is not available."
    curses.endwin()
    print msg

if __name__ == '__main__':
    main()
