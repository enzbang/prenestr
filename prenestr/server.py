#!/usr/bin/env python

import io
import os
import sys

from probe import Probe
from daemon import Daemon

import Xlib


# Configuration
DAEMON_FIFO = '/tmp/prenestr.fifo'
DAEMON_PID = '/tmp/prenestr.pid'
DAEMON_LOG = '/tmp/prenestr.log'


PROBE = Probe()


def debug(msg):
    with open(DAEMON_LOG, "a") as f:
        f.write(msg + '\n')


class X(object):

    def __init__(self):
        self.wgap = 10
        self.hgap = 25
        self.windows = {}

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
        for w in self.windows[current_desktop]:
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
        dw = [windows[w].copy() for w in desk_windows]
        for w in dw:
            # Can't dump xobj data
            del w['xobj']
        self.windows[current_desktop] = dw

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


class Prenestr(Daemon):

    def run(self):
        x = X()
        if os.path.exists(DAEMON_FIFO):
            os.remove(DAEMON_FIFO)
        try:
            os.mkfifo(DAEMON_FIFO)
        except OSError, e:
            sys.exit("Failed to create FIFO: %s", e)
        else:
            while True:
                for line in io.open(DAEMON_FIFO):
                    command = line.strip()
                    if hasattr(x, command):
                        getattr(x, command)()
                    else:
                        debug("%s command not found" % command)
