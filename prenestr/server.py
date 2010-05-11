#!/usr/bin/env python

from Xlib.display import Display
from Xlib import X, Xatom
from Xlib import protocol

K_G = 30
K_H = 44
K_L = 33
K_T = 45
K_ENTER = 36


class Prenestr(object):

    def __init__(self):
        self.ratio = 0.5
        self.wborder = 10
        self.hborder = 30
        self.disp = Display()
        self.root = self.disp.screen().root

        # we tell the X server we want to catch keyPress event
        self.root.change_attributes(event_mask=X.KeyPressMask)

        self.grab_key(K_L)
        self.grab_key(K_H)
        self.grab_key(K_L, X.Mod4Mask | X.ShiftMask)
        self.grab_key(K_H, X.Mod4Mask | X.ShiftMask)
        self.grab_key(K_T)
        self.grab_key(K_ENTER)
        while True:
            event = self.root.display.next_event()
            if event.type == X.KeyPress:
                self.keypress(event)

    def get_active(self):
        id = self.root.get_full_property(
            self.disp.intern_atom("_NET_ACTIVE_WINDOW"), 0).value[0]
        obj = self.disp.create_resource_object('window', id)
        return (id, obj)

    def _send_event(self, win, ctype, data, mask=None):
        data = (data + ([0] * (5 - len(data))))[:5]
        ev = protocol.event.ClientMessage(window=win,
                                          client_type=ctype, data=(32, (data)))
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask)

    def workarea(self):
        v = self.root.get_full_property(
            self.disp.intern_atom("_NET_WORKAREA"), 0).value
        return v[0], v[1], v[2], v[3]

    def move(self, win, to='left', y_pos=0, y_nbwin=1):
        id, obj = win
        rx, ry, rw, rh = self.workarea()

        if to == 'left':
            x = rx
            y = ry
            w = rw * self.ratio - self.wborder
            h = rh
        elif to == 'right':
            x = rx + rw * self.ratio + self.wborder
            y = ry + y_pos * (rh / y_nbwin)
            w = rw * (1 - self.ratio) - self.wborder
            h = rh / y_nbwin
            if y_nbwin > 1:
                h = h - self.hborder

        # Reset state
        self._send_event(id,
                self.disp.intern_atom("_NET_WM_STATE"),
                [0, self.disp.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT"),
                    self.disp.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ")])
        obj.configure(x=x, y=y, width=w, height=h, stack_mode=X.Above)
        self._send_event(id,
                self.disp.intern_atom("_NET_ACTIVE_WINDOW"), [])
        self.disp.flush()

    def grab_key(self, key, mask=X.Mod4Mask, ungrab=False):
        self.root.grab_key(key, mask, 1, X.GrabModeAsync, X.GrabModeAsync)
        if ungrab:
            self.ungrab_list.append(key)

    def ungrab_key(self, key, mask=X.Mod4Mask):
        self.root.ungrab_key(key, mask, 1)

    def tile(self, master='position'):
        current_window = self.get_active()
        win_list = self.root.get_full_property(
            self.disp.intern_atom("_NET_CLIENT_LIST"),
            Xatom.WINDOW).value
        current_desktop = self.root.get_full_property(
            self.disp.intern_atom("_NET_CURRENT_DESKTOP"), 0).value[0]
        desk_list = []
        for win_id in win_list:
            obj = self.disp.create_resource_object('window', win_id)
            windesk = obj.get_full_property(
                self.disp.intern_atom("_NET_WM_DESKTOP"), 0).value[0]
            if windesk == current_desktop:
                desk_list.append((win_id, obj))

        if not desk_list:
            return

        def get_geom(window):
            wg = window.get_geometry()
            tl = window.translate_coords(self.root, wg.x, wg.y)
            return (-tl.x, -tl.y, wg.width, wg.height)

        geom = [(w, get_geom(w[1])) for w in desk_list]

        if master == 'position':
            left = min(geom, key=lambda l: l[1][0])[0]
        else:
            left = current_window

        self.move(left, to="left")
        others = [w for w in geom if w[0][0] != left[0]]
        others.sort(key=lambda l: l[1][1])

        for pos, win in enumerate(others):
            self.move(win[0], to="right", y_pos=pos, y_nbwin=len(others))


        # Reactivate window
        self._send_event(current_window[0],
                         self.disp.intern_atom("_NET_ACTIVE_WINDOW"), [])

        return

    def keypress(self, event):

        if event.detail == K_H:
            if event.state & X.ShiftMask:
                self.ratio -= 0.1
                if self.ratio < 0:
                    self.ratio = 0
                self.tile()
            else:
                self.move(self.get_active())
        elif event.detail == K_L:
            if event.state & X.ShiftMask:
                self.ratio += 0.1
                if self.ratio > 1:
                    self.ratio = 1
                self.tile()
            else:
                self.move(self.get_active(), to='right')
        elif event.detail == K_T:
            self.tile()
        elif event.detail == K_ENTER:
            self.tile(master='active')

if __name__ == '__main__':
    Prenestr()
