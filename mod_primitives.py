import math


class LFO:

    def __init__(self, shape="sine", freq=1, amp=1, offset=0):
        self.shape = shape
        self.freq = freq
        self.amp = amp
        self.offset = offset
        self.t = 0

    def update(self, dt):
        self.t += dt
        phase = self.t * self.freq * 2 * math.pi

        if self.shape == "sine":
            v = math.sin(phase)
        elif self.shape == "triangle":
            v = 2 * abs((phase / math.pi) % 2 - 1) - 1
        elif self.shape == "square":
            v = 1 if math.sin(phase) > 0 else -1
        else:
            v = 0

        return v * self.amp + self.offset


class Envelope:

    def __init__(self, attack=0.1, decay=0.2, sustain=0.5, release=0.3):
        self.a, self.d, self.s, self.r = attack, decay, sustain, release
        self.t = 0
        self.active = False

    def trigger(self):
        self.t = 0
        self.active = True

    def update(self, dt):
        if not self.active:
            return 0

        self.t += dt

        if self.t < self.a:
            return self.t / self.a

        if self.t < self.a + self.d:
            return 1 - (1 - self.s) * ((self.t - self.a) / self.d)

        return self.s
