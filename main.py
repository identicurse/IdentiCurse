#!/usr/bin/env python
from identicurse import IdentiCurse
import random
slogans = [
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
            "trying to do teh frees"
          ]

# Innit.
print "Welcome to IdentiCurse 0.1 (Aberystwyth) - %s." % (random.choice(slogans))
IdentiCurse()
