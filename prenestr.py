#!/usr/bin/env python

import os
import select
import sys

from probe import Probe
from cPickle import dump, load
import Xlib


PROBE = Probe()

def debug(msg):
    if 'debug' in sys.argv:
        print msg


class X:

    def __init__(self):
        self.wgap = 10
        self.hgap = 25

    def right(self, window=None, y_start=None, nb_win=1):
        self.move(True, window, y_start, nb_win)

    def left(self, window=None, y_start=None, nb_win=1):
        self.move(False, window, y_start, nb_win)

    def get_active(self):
        self._id = str(PROBE.get_active_window_id())
        self._active_w = PROBE.get_window_by_id(long(self._id, 16))
        self._active = self._active_w['xobj']

    def move(self, right, window, y_start, nb_win):
        current_desktop = PROBE.get_desktops()[PROBE.get_desktop()]
        if window is None:
            self.get_active()
            window = self._active
        if y_start is None:
            y_start = current_desktop.get('y')
        else:
            if y_start:
                y_start = (
                        current_desktop.get('height')
                        / nb_win) * y_start + self.hgap
            else:
                y_start = 0

        if right:
            x_start = current_desktop.get('width') / 2 + self.wgap
        else:
            x_start = 0
        debug("move %s %s y_start: %d (/%d)" % (
            window or "CURRENT",
            right and "Right" or "Left",
            y_start,
            nb_win))
        PROBE.window_resize(
                window,
                x_start,
                y_start,
                current_desktop.get('width') / 2 - self.wgap,
                current_desktop.get('height') / nb_win - self.hgap)
        if window is None:
            PROBE.window_activate(self._active)

    def restore(self):
        current_desktop = PROBE.get_desktop()
        if not os.path.exists("/tmp/plwm.windows.%d" % current_desktop):
            debug("Nothing to restore")
            return
        with open("/tmp/plwm.windows.%d" % current_desktop) as btile:
            windows = load(btile)
        for w in windows:
            if not w['hidden']:
                try:
                    PROBE.window_resize(
                            PROBE.get_window_by_id(long(w['id'], 16))['xobj'],
                            int(w['x']),
                            int(w['y']),
                            int(w['width']),
                            int(w['height']))
                except Xlib.error.BadWindow:
                    pass
        os.remove("/tmp/plwm.windows.%d" % current_desktop)

    def tile(self):
        current_desktop = PROBE.get_desktop()
        # Active on left
        self.get_active()
        self.left()
        windows = PROBE.get_windows()
        desk_windows = [
                w for w in windows
                if windows[w]['desktop'] == current_desktop
                and w != self._id and not windows[w]['hidden']]
        if not os.path.exists("/tmp/plwm.windows.%d" % current_desktop):
            with open("/tmp/plwm.windows.%d" % current_desktop, "w") as btile:
                dw = [windows[w].copy() for w in desk_windows]
                for w in dw:
                    # Can't dump xobj data
                    del w['xobj']
                dump(dw, btile)

        # Remove ACTIVE
        nb_win = len(desk_windows)
        debug("%d windows" % nb_win)
        for pos, w in enumerate(desk_windows):
            self.right(windows[w]['xobj'], pos, nb_win)
        PROBE.window_activate(self._active)

    def max_all(self):
        current_desktop = PROBE.get_desktop()
        # Active on left
        self.get_active()
        self.left()
        windows = PROBE.get_windows()
        desk_windows = [
                w for w in windows
                if windows[w]['desktop'] == current_desktop]
        # Remove ACTIVE
        for pos, w in enumerate(desk_windows):
            PROBE.window_maximize(windows[w]['xobj'])
        PROBE.window_activate(self._active)

    def max_vert(self):
        current_desktop = PROBE.get_desktops()[PROBE.get_desktop()]

        self.get_active()
        PROBE.window_resize(
                self._active,
                int(self._active_w['x']),
                current_desktop.get('y'),
                int(self._active_w['width']),
                int(current_desktop.get('height')))


    def quit(self):
        debug("Goodbye")
        exit(0)


def init():
    with open("/tmp/plwm.pid", "w") as fpid:
        fpid.write(str(os.getpid()))
    x = X()
    fifoname = os.path.join('/tmp', 'plwm.fifo')
    if os.path.exists(fifoname):
        os.remove(fifoname)
    try:
        os.mkfifo(fifoname)
    except OSError, e:
        print "Failed to create FIFO: %s", e
    else:
        fifo = os.open(fifoname, os.O_RDONLY)
        while True:
            if select.select([fifo], [], []):
                buf = os.read(fifo, 100)
                if buf:
                    command = buf.strip()
                    if hasattr(x, command):
                        getattr(x, command)()
                    else:
                        debug("%s command not found" % command)


if __name__ == '__main__':
    init()
