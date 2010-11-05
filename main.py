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
            "Got GNOME git commit access"
          ]

# Innit.
print "Welcome to IdentiCurse - %s." % (random.choice(slogans))
IdentiCurse()
