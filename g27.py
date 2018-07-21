#!/usr/bin/env python
"""
http://upgrayd.blogspot.de/2011/03/logitech-dual-action-usb-gamepad.html

G27
===
example::

    A0 B7 A3 04 5C 7D 02 02
     0  1  2  3  4  5  6  7


    0, 1, 2, 3: sequence, little endian
    3, 5: value, little endian
    6: group
    7: axis

NOTE! From here on, I talk big endian -- also in hex!

Wheel values::

            left               dead           right
            <-------------------XX---------------->
    dec     32769      65535     0      1     32767
    hex     80 01      ff ff  00 00 00 01     7F FF


Pedal values:

- no pressure: 7F FF
- halfway: 00 00
- full: 80 01
"""
from binascii import hexlify


# 32769 -> 0
# 0 -> 0.5
# 65535 -> 0.49
# 32767 -> 1
def _normalize(x):
    if 32769 <= x <= 65535:
        return (x - 32769) / 65535
    elif 0 == x:
        return 0.5
    elif 0 < x <= 32767:
        return (x + 32768) / 65535


def powergenerator(start=0):
    """Generate powers of 256"""
    i = start
    while True:
        yield 256 ** i
        i += 1


class Bytewurst(object):

    def __init__(self, bs):
        self.raw = bs
        self.ints = [x for x in bs]

    def __repr__(self):
        return ' '.join(map(hexlify, self.raw))

    @property
    def int(self):
        r"""
        For "01 00 03 0A" ints would be [1, 0, 3, 10], so::

            >>> bs = '\x01\x00\x03\x0A'
            >>> bw = Bytewurst(bs)
            >>> bw.int == (1 * 1) + (0 * 256) + (3 * 65536) + (10 * 16777216)
            True
        """
        return sum(a * b for a, b in zip(self.ints, powergenerator()))

    @property
    def hex(self):
        return hexlify(self.raw)

    @property
    def bits(self):
        return ' '.join([format(x, '08b') for x in self.ints])


BUTTON2NAME = """
0200=wheel axis
0105=paddle left
0104=paddle right
0107=wheel button left 1
0114=wheel button left 2
0115=wheel button left 3
0106=wheel button right 1
0112=wheel button right 2
0113=wheel button right 3
0201=clutch
0203=brake
0202=gas
0101=shifter button left
0102=shifter button right
0103=shifter button up
0100=shifter button down
0204=dpad left/right
0205=dpad up/down
010b=shifter button 1
0108=shifter button 2
0109=shifter button 3
010a=shifter button 4
010c=gear 1
010d=gear 2
010e=gear 3
010f=gear 4
0110=gear 5
0111=gear 6
0116=gear R
"""
def f():
    for line in BUTTON2NAME.strip().split('\n'):
        a, b = line.split('=')
        yield a.encode('ascii'), b
button2namedict = dict(f())


class Button(Bytewurst):
    def __init__(self, bs):
        super().__init__(bs)
        self.name = button2namedict.get(self.hex, 'UNKNOWN: %s' % self.hex)


class Value(Bytewurst):
    def __repr__(self):
        if self.int == 0:
            return '  off'
        elif self.int == 1:
            return '   on'
        else:
            print(self.hex)
            return '%5d' % self.int

    @property
    def normalized(self):
        return _normalize(self.int)


class Message(object):

    FMT_HEX = '%02X'
    FMT_DEC = '%03d'

    def __init__(self, bs):
        self.bs = bs
        self.raw_seq = bs[0:4]
        self.raw_value = bs[4:6]
        self.raw_id = bs[6:8]
        self.ints = [x for x in bs]
        self.sequence = Bytewurst(bs[0:4])
        self.value = Value(bs[4:6])
        self.button = Button(bs[6:8])

    def __repr__(self):
        return f'{self.sequence.int} {self.button.name:>8} {self.value.normalized:5.0%}'

    @property
    def hex(self):
        """
        Human-readable hex format. LITTLE ENDIAN!
        """
        return ' '.join(self.FMT_HEX % x for x in self.ints)

    @property
    def bit(self):
        return ' '.join([self.sequence.bits, self.value.bits, self.button.bits])

    @property
    def grouped_hex(self):
        return f'{self.sequence.int:06x} {self.value.int:04x} {self.button.int:04x}'

    @property
    def dec(self):
        """Human-readable decimal format"""
        return ' '.join(self.FMT_DEC % x for x in self.ints)


def loop(handler):
    with open('/dev/input/js0', 'rb') as device:
        while True:
            bs = device.read(8)
            handler(bs)


def print_message(bs):
    message = Message(bs)
    print(message)


if __name__ == '__main__':
    loop(print_message)
    # loop(print)
    # loop(lambda x: print(Message(x).grouped_hex))
    # loop(lambda x: print(Message(x).hex))
