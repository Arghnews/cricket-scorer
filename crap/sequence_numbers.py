#!/usr/bin/env python3

import sys

if sys.platform == "esp8266":
    import uos
else:
    import random

class SequenceNumber(object):
    "Class wrapping 4 byte unsigned sequence numbers"

    __slots__ = ("n", "bits")

    def __init__(self, n = None, bits = 3):
        assert bits >= 2
        # while not n:
        if n is None:
            if sys.platform == "esp8266":
                # TODO: add comment about sys.byteorder being unused
                # n = int.from_bytes(uos.urandom(size), sys.byteorder)
                raise Exception("Not implemented yet")
            else:
                n = random.randint(0, 2 ** bits - 1)
        self.n = n
        self.bits = bits

    def increment(self):
        if self._sequence_number == 4294967294:
            self._sequence_number = 0
        else:
            self._sequence_number = self._sequence_number + 1

    def __lt__(self, other):
        a, b, n = self.n, other.n, self.bits
        # print(b, (a + 2 ** (n - 1)) % n)
        c = 2 ** (n - 1)
        C = 2 ** n
        # print("{} <= (({} + {}) % {})".format(b, a, c, (2 ** n)))
        if a == b:
            return False
        # elif a < b:
        else:
            c = (a + 4) % 8
            if a < c:
                return b > a and b <= c
            else:
                return b > a or b < c
            # c = (a + 4) % 8
            # if a < c:
            #     return b > a and b <= c
            # else:
            #     return b > a or b < c

            # d = (a + c) % (2 ** n)

            # return b < (a + 4) % C
            # print("")
            # print("a: {}, b: {}".format(a, b))
            # print("b > a or ((d - b) % C) > 0")
            # print("{} > {} or (({} - {}) % {}) > 0".format(b, a, d, b, C))
            # return (b - a) % C > 0 and ((d - b) % C) > 0
            # e = (b + c) % (2 ** n)
            # print(a, b, c, d, e)
            # return a <= (b + c) % (2 ** n)
        # else:
        #     return a <= (b + c) % (2 ** n)
        # Fails for case 1 < 7 because misses a case
        # if self.n == x:
        #     return False
        # elif self.n < x:
        #     return self.n < x
        # else:
        #     mid = (2 ** (self.bits - 1))
        #     # print("(({} - {}) % {} <= {}".format(x, self.n, (2 ** self.bits), mid))
        #     return ((x - self.n) % (2 ** self.bits)) <= mid
# x, mid = other.n - self.n, (2 ** (self.bits - 1))
        # print(x)
        # neg = - (2 ** self.bits) - 1 <= x <= - mid
        # pos = 0 < x <= mid
        # print(0, "<", o, "<=", (2 ** self.bits - 1))
        # print(neg, pos)
        # return neg or pos

    def __str__(self):
        return "{:,}".format(self.n)

def main(argv):
    s = SequenceNumber(5)
    for i in range(8):
        s2 = SequenceNumber(i)
        # s < s2
        print(s, "<", s2, s < s2)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
