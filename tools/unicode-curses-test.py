#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script simulates how the identicurse gathers data from the textbox. It
currnely works on a per character basis, so when pasting make sure you don't
include any spaces!

For some reason the inch() method doesn't always return the same character that
was put on the screen by addstr(), certain CJK characters seem to be affected
by this.

Try out some of these characters:
ß ä € £ シ ﺖ ︽ 丈 ゐ カ 𝀋 𝀧  𝅘𝅥𝅯 ✌ ║ 을 지
û Đ ศ ฿ ๖ ق Ж Щ р დ ღ ჵ Ⴏ Ⴋ Ⴕ თ ḡ Ṍ ỹ  ຽ

http://theorem.ca/~mvcorks/code/charsets/auto.html

"""

from os import system
import curses
import locale

locale.resetlocale()

def utf_demangle(screen, utf_ch):
    #liberated from http://groups.google.com/group/comp.lang.python/browse_thread/thread/67dce30f0a2742a6?fwc=2&pli=1
    def check_next_byte():
        utf_ch = screen.getch()
        if 128 <= utf_ch <= 191:
            return utf_ch
        else:
            raise UnicodeError

    bytes = []
    bytes.append(utf_ch)
    if 194 <= utf_ch <= 223:
        #2 bytes
        bytes.append(check_next_byte())
    elif 224 <= utf_ch <= 239:
        #3 bytes
        bytes.append(check_next_byte())
        bytes.append(check_next_byte())
    elif 240 <= utf_ch <= 244:
        #4 bytes
        bytes.append(check_next_byte())
        bytes.append(check_next_byte())
        bytes.append(check_next_byte())

    buf = "".join([chr(b) for b in bytes])

    return buf.decode('utf-8')

screen = curses.initscr()
x = ord(u'ß')
output = u'ß'
try:
    while x != ord('4'):
        screen.clear()
        screen.border(0)
        screen.addstr(2, 2, "Type in a character...")
        screen.addstr(4, 2, output.encode('utf-8'))
        screen.addstr(5, 2, str(ord(output)))

        gather = screen.inch(4, 2)
        screen.addstr(8, 2, unichr(gather).encode('UTF-8'))
        screen.addstr(9, 2, str(gather))
        screen.refresh()

        x = screen.getch()
        output = utf_demangle(screen, x)
finally:
    curses.endwin()
