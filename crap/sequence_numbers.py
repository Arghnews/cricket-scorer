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
# No copy module in esp micropython port

# Design choice No. 1 - it is possible to overload operators in such a way that
# statements like this work - 5 < sequence_number
# However sequence numbers with these half interval modulo arithmetic type
# properties are unintuitive and we probably don't want users (me) to forget this
# and expect them to work like normal ints when compared. Therefore will only
# allow comparing SequenceNumbers with other SequenceNumbers and force user to
# explicitly state conversion to int with int(). Same applies for congruence on
# equality (in addition to the aforementioned ordering).
# Ie. for a 3 bit number
# SequenceNumber(n = 1, bits = 3) == 1 # True
# SequenceNumber(n = 1, bits = 3) == 9 # True? # Ie. congruent modulo 8 but quite
# possibly unintuitive given the wrong context whereas of course this works
# SequenceNumber(n = 1, bits = 3) == SequenceNumber(n = 9, bits = 3) # True

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

    def __copy__(self):
        return SequenceNumber(n = self.n, bits = self.bits)

    # Does adding two sequence numbers together make sense? Certainly you want
    # to add an integer to a sequence number, but two together?
    # Unsure if this is the cleanest/"right" way to do this
    def __iadd__(self, other):
        if type(other) is not int:
            return NotImplemented
        # if type(other) is not in (type(self), int):
        # print("__iadd__", self, "to", other, type(other))
        self.n = (self.n + other) % (2 ** self.bits)
        return self

    def __add__(self, other):
        # return NotImplemented
        # print("__add__", self, "to", other, type(other))
        return self.__copy__().__iadd__(other)

    def __radd__(self, other):
        # print("__radd__", self, "to", other, type(other))
        # return 11
        return self.__add__(other)

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
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
        if type(self) is not type(other):
            return NotImplemented
        return self.n == other.n

    def __int__(self):
        return self.n

    def __str__(self):
        return "{:,}".format(self.n)

    def __bytes__(self):
        return int_to_bytes(self.n, self.bits)

    # Python spec says this is default generated when __eq__ is defined
    # TODO: check this on esp8266 micropython port
    # def __ne__(self, other):
    #     return not self == other

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

def int_to_bytes(n, bits):
    # For a positive integer n, outputs bits number of bits as bytes (LE)
    # n = (1 << 16) + (1 << 15) + 63
    # n = 0x0123456789ABCDEF
    # 0x0123456789ABCDEF -> 64 bit LE - EF CD AB 89 67 45 23 01
    # bits = 64
    assert n >= 0 and bits >= 0
    b = bytearray()
    while bits > 0:
        b.append(sum(n & 2 ** i for i in range(min(8, bits))))
        n >>= 8
        bits -= min(8, bits)
    return bytes(b)



def main(argv):

    # For a positive integer n, outputs bits number of bits as bytes (LE)
    n = (1 << 16) + (1 << 15) + 63
    n = 0x0123456789ABCDEF
    # 0x0123456789ABCDEF -> 64 bit LE - EF CD AB 89 67 45 23 01
    bb = int_to_bytes(n, 64)
    acc = 0
    i = 0
    for i, b in enumerate(bb):
        acc |= b << i * 8
    print(hex(acc))
    return

    return

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

    # s, s2 = SequenceNumber(6), SequenceNumber(7)
    # print("s:", s, ", s2:", s2)
    # print("s = s + s2")
    # s = s + s2
    # print("s:", s, ", s2:", s2)
    # print("")

    # s, s2 = SequenceNumber(6), SequenceNumber(7)
    # print("s:", s, ", s2:", s2)
    # print("s += s2")
    # s += s2
    # print("s:", s, ", s2:", s2)
    # print("")

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

    # 5 > s2
    # 5 < s2
    # s2 > 5
    # s2 < 5
    # s2 >= 5
    # s2 <= 5
    print(s == 5)
    print(5 == s)
    print(5 != s)
    print(int(s))

    print(dir(s))
    print("")
    print(s.n)
    # This generic way is the worst kind of generic where it will silently
    # "work" if other callables members are inserted into the class -
    # something that is a class or something with a __call__ function. Not
    # lambdas surprisingly. Also doesn't deal with deepcopy or not.
    # Advantage is this allows for internal copy ctor without user facing one if
    # needed by memberwise copying. Also no overhead of recalling ctor with same
    # args.
    print([attr for attr in dir(s) if not callable(getattr(s, attr)) and not attr.startswith("__")])
    # print(vars(s))

    ss = SequenceNumber(n = 0, bits = 3)
    for i in range(32):
        print(i, ss)
        # print(int(ss))
        assert i % 8 == int(ss)
        ss += 1

class A: pass
class B(A): pass

if __name__ == "__main__":
    sys.exit(main(sys.argv))
