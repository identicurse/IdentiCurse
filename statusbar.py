import threading, time

class StatusBar(object):
    def __init__(self, window):
        self.window = window
        self.left_text = ""
        self.right_text = ""

    def update_left(self, text):
        self.left_text = text
        self.update()
    
    def update_right(self, text):
        self.right_text = text
        self.update()

    def timed_update_left(self, text, delay=10):
        TimedUpdate(self, 'left', text, delay).start()

    def timed_update_right(self, text, delay=10):
        TimedUpdate(self, 'right', text, delay).start()

    def update(self):
        self.window.erase()
        self.window.addstr(0, 0, self.left_text)
        right_x = self.window.getmaxyx()[1] - (len(self.right_text) + 2)
        self.window.addstr(0, right_x, self.right_text)
        self.window.refresh()

class TimedUpdate(threading.Thread):
    def __init__(self, statusbar, side, text, delay):
        threading.Thread.__init__(self)

        self.statusbar = statusbar
        self.side = side
        self.text = text
        self.delay = delay

    def run(self):
        initial_value = getattr(self.statusbar, self.side + "_text")

        update_function = getattr(self.statusbar, "update_" + self.side)
        update_function(self.text)

        time.sleep(self.delay)

        update_function(initial_value)
