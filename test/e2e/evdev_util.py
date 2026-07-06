import time

from evdev import ecodes


class EventWatcher:
    """Reads EV_KEY / EV_REL events from a grabbed evdev device."""

    def __init__(self, device):
        self.device = device
        self.events = []  # list of (type, code, value)

    def grab(self):
        self.device.grab()

    def ungrab(self):
        try:
            self.device.ungrab()
        except Exception:
            pass

    def collect(self, timeout=0.5):
        """Drain events for `timeout` seconds into self.events."""
        self.events = []
        end = time.time() + timeout
        while time.time() < end:
            ev = self.device.read_one()
            if ev is not None:
                if ev.type in (ecodes.EV_KEY, ecodes.EV_REL):
                    self.events.append((ev.type, ev.code, ev.value))
            else:
                time.sleep(0.002)
        return self.events

    def saw_key(self, code, value):
        return any(t == ecodes.EV_KEY and c == code and v == value
                   for (t, c, v) in self.events)

    def saw_rel(self, code, negative=None):
        for (t, c, v) in self.events:
            if t == ecodes.EV_REL and c == code:
                if negative is None:
                    return True
                if negative and v < 0:
                    return True
                if (not negative) and v > 0:
                    return True
        return False
