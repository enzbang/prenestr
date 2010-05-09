
from Xlib.display import Display
from Xlib import X
from Xlib import protocol

K_G = 30
K_H = 44
K_L = 33


class Prenestr(object):


    def __init__(self):
        self.disp = Display()
        self.root = self.disp.screen().root

        # we tell the X server we want to catch keyPress event
        self.root.change_attributes(event_mask=X.KeyPressMask)

        active = self.get_active()
        self.move(active)

        self.grab_key(K_L)
        self.grab_key(K_H)
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
        ev = protocol.event.ClientMessage(window=win, client_type=ctype, data=(32, (data)))
        self.root.send_event(ev, event_mask=X.SubstructureRedirectMask)

    def move(self, win, to='left'):
        id, obj = win
        root_geo = self.root.get_geometry()

        if to == 'left':
            x = root_geo.x
            y = root_geo.y
            w = root_geo.width / 2 - 10 # 10 border
            h = root_geo.height
        elif to == 'right':
            x = root_geo.x + root_geo.width / 2 + 10
            y = root_geo.y
            w = root_geo.width / 2 - 10 # 10 border
            h = root_geo.height

        # Reset state
        self._send_event(id,
                self.disp.intern_atom("_NET_WM_STATE"),
                [0, self.disp.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT"),
                    self.disp.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ")])
        obj.configure(x=x, y=y, width=w, height=h, stack_mode=X.Above)
        #self.disp.flush()

        self._send_event(id,
                self.disp.intern_atom("_NET_ACTIVE_WINDOW"), [])
        self.disp.flush()

    def grab_key(self, key, mask=X.Mod4Mask, ungrab=False):
        self.root.grab_key(key, mask, 1, X.GrabModeAsync, X.GrabModeAsync)
        if ungrab:
            self.ungrab_list.append(key)

    def ungrab_key(self, key, mask=X.Mod4Mask):
        self.root.ungrab_key(key, mask, 1)

    def keypress(self, event):
        if event.detail == K_H:
            self.move(self.get_active())
        elif event.detail == K_L:
            self.move(self.get_active(), to='right')

if __name__ == '__main__':
    Prenestr()
