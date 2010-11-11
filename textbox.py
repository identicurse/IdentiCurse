import curses
from curses import textpad

class Textbox(textpad.Textbox):
    def __init__(self, win, insert_mode=False):
        try:
            textpad.Textbox.__init__(self, win, insert_mode)
        except TypeError:  # python 2.5 didn't support insert_mode
            textpad.Textbox.__init__(self, win)
        
    def edit(self):
        while 1:
            ch = self.win.getch()
            
            if ch == 127:
                self.do_command(263)
                
            if ch == curses.KEY_ENTER or ch == 10:
                break
            
            if not ch:
                continue
            
            if not self.do_command(ch):
                break
            
            self.win.refresh()
            
        return self.gather()
