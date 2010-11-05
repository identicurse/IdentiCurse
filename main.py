#!/usr/bin/env python
from identicurse import IdentiCurse
import random
slogans = [
            "100% hippie-approved",
            "powered by hatred",
            "we don't get OAuth either",
            "don't drink and dent",
          ]

# Innit.
print "Welcome to IdentiCurse - %s." % (random.choice(slogans))
IdentiCurse()
