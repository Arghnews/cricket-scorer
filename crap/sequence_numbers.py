#!/usr/bin/env python3

import sys

# TODO: https://docs.python.org/3/reference/datamodel.html#object.__bytes__
# Has a to bytes method that's not pickle built in, use it
# Add the add method operator overload - consider __add__, __radd__, __iadd__
# __add__ -> x + y calls x.__add__(y)
# __radd__ -> x + y calls y.__add__(x) if x.__add__(y) returns NotImplemented
# __iadd__ -> These methods should attempt to do the operation in-place
# (modifying self) and return the result (which could be, but does not have to
# be, self). If a specific method is not defined, the augmented assignment falls
# back to the normal methods. For instance, if x is an instance of a class with
# an __iadd__() method, x += y is equivalent to x = x.__iadd__(y) . Otherwise,
# x.__add__(y) and y.__radd__(x) are considered, as with the evaluation of x + y
# - ie. in-place version returning self

if sys.platform == "esp8266":
    import uos
else:
    import random

# Subclassing object was here for a reason (not old style classes but another
# actually relevant reason in this Python3 project but I didn't write it down
# and have now forgotten..
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

    # Could overload __int__(self) -> int ?

    def __add__(self, other):
        # return NotImplemented
        print("__add__", self, "to", other, type(other))
        return 10

    def __radd__(self, other):
        print("__radd__", self, "to", other, type(other))
        return 11

    def __iadd__(self, other):
        print("__iadd__", self, "to", other, type(other))
        return self

    def __lt__(self, other):
        a, b = self.n, other.n
        c = (a + (2 ** (self.bits - 1))) % (2 ** self.bits)
        if a < c: # Non wrapping case
            return a < b and b <= c
        else: # Wrapping case
            return a < b or b <= c

    def __le__(self, other):
        return self.n == other.n or self < other

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return other <= self

    def __eq__(self, other):
        return self.n == other.n

    def __ne__(self, other):
        return not self == other

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
    s = SequenceNumber(6)
    s2 = SequenceNumber(7)
    for i in range(8):
        s2 = SequenceNumber(i)
        # s < s2
        # print(s, "<", s2, s < s2)

    print("s + 5")
    s + 5
    print("")

    print("5 + s")
    5 + s
    print("")

    print("s += 5")
    s += 5
    print("")


    s, s2 = SequenceNumber(6), SequenceNumber(7)
    print("s:", s, ", s2:", s2)
    print("s = s + 5")
    s = s + 5
    print("s:", s, ", s2:", s2)
    print("")

    s, s2 = SequenceNumber(6), SequenceNumber(7)
    print("s:", s, ", s2:", s2)
    print("s = 5 + s")
    s = 5 + s
    print("s:", s, ", s2:", s2)
    print("")

    s, s2 = SequenceNumber(6), SequenceNumber(7)
    print("s:", s, ", s2:", s2)
    print("s = s + s2")
    s = s + s2
    print("s:", s, ", s2:", s2)
    print("")

    s, s2 = SequenceNumber(6), SequenceNumber(7)
    print("s:", s, ", s2:", s2)
    print("s += s2")
    s += s2
    print("s:", s, ", s2:", s2)
    print("")

    s, s2 = SequenceNumber(6), SequenceNumber(7)
    print("s:", s, ", s2:", s2)
    print("s += 5")
    s += 5
    print("s:", s, ", s2:", s2)
    print("")

    print(s < s2)
    print(s == s)
    print(s != s)
    print(s != s2)
    print(s > s2)
    print(s2 >= s)
    print(s2 >= s2)

    print(B is A)
    print(issubclass(B, A))

    print(isinstance(A(), A))
    print(isinstance(B(), A))
    print(isinstance(B(), B))
    print(isinstance(A(), B))

class A: pass
class B(A): pass

if __name__ == "__main__":
    sys.exit(main(sys.argv))
