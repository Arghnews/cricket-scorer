#!/usr/bin/env python3

import sys

from .utility import int_to_bytes

# A note on this file:
# Much of it was written back when a micropython port on an esp8266 was being
# targeted. Now that is not the case. However, since it works, I'm going to
# leave it as is.

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


# Subclassing object was here for a reason (not old style classes but another
# actually relevant reason in this Python3 project but I didn't write it down
# and have now forgotten..)
class SequenceNumber(object):
    "Class wrapping 4 byte unsigned sequence numbers"

    __slots__ = ("n", "bits")

    def __init__(self, n=None, *, bits=None, bytes_=None):
        assert (bits is None) ^ (bytes_ is None)  # Exactly one is provided
        if bytes_ is not None:
            bits = bytes_ * 8
        assert bits >= 2

        if type(n) is bytes:
            n = int.from_bytes(n, sys.byteorder)
        elif type(n) is int:
            pass
        elif n is None:
            n = 0
        else:
            assert False, "Unreachable"

        # TODO: just gen sequence numbers as 0 if none?
        self.n = n % (2**bits)
        self.bits = bits

    def post_increment(self):
        cp = self.__copy__()
        self += 1
        return cp

    def __copy__(self):
        return SequenceNumber(n=self.n, bits=self.bits)

    # Does adding two sequence numbers together make sense? Certainly you want
    # to add an integer to a sequence number, but two together?
    # Unsure if this is the cleanest/"right" way to do this
    def __iadd__(self, other):
        if type(other) is not int:
            return NotImplemented
        # if type(other) is not in (type(self), int):
        # print("__iadd__", self, "to", other, type(other))
        self.n = (self.n + other) % (2**self.bits)
        return self

    def __add__(self, other):
        # return NotImplemented
        # print("__add__", self, "to", other, type(other))
        return self.__copy__().__iadd__(other)

    def __radd__(self, other):
        # print("__radd__", self, "to", other, type(other))
        # return 11
        return self.__add__(other)

    def __sub__(self, other):
        print("sub other is:", other)
        return self.__add__(-other)

    def __isub__(self, other):
        print("Isub")
        return self.__iadd__(-other)

    # rsub is confusing

    # def _type_check_(self, other):
    #     if type(self) is not type(other) or self.bits != other.bits:
    #         return NotImplemented
    #     return True

    # TODO: finish these operators in terms of each other

    # Comparing SequenceNumbers that don't share the same number of bits could
    # be VERY confusing. Especially given the modulo arithmetic already...
    # I'm sure it's possible to come up with painful examples by jigging about
    # with bits etc.
    # Let's force the number of bits to be the same else return NotImplemented
    # Otherwise the user can always convert to int and do as they please
    def __lt__(self, other):
        if type(self) is not type(other) or self.bits != other.bits:
            return NotImplemented
        a, b = self.n, other.n
        c = (a + (2**(self.bits - 1))) % (2**self.bits)
        if a < c:  # Non wrapping case
            return a < b and b <= c
        else:  # Wrapping case
            return a < b or b <= c

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other):
        if type(self) is not type(other) or self.bits != other.bits:
            return NotImplemented
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    # We are strict as what should things like
    # SequenceNumber(n = 6, bits = 3) == SequenceNumber(n = 14, bits = 4) # ?
    # "Clearly" 6 != 14 but n = 6 == 14 % (2 ** 3) == 6
    # Can always convert to ints
    # To me currently it seems this behaviour is unobvious at best
    def __eq__(self, other):
        if type(self) is not type(other) or self.bits != other.bits:
            return NotImplemented
        return self.n == other.n

    # Micropython does not seem to call this as would expect - add additional
    # explicit function
    def __int__(self):
        return self.n

    def __str__(self):
        return "{:,}".format(self.n)

    def __bytes__(self):
        return int_to_bytes(self.n, self.bits // 8 + int(self.bits % 8 != 0))

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

# The below is left here as it's used as testing


def main(argv):

    # For a positive integer n, outputs bits number of bits as bytes (LE)
    n = (1 << 16) + (1 << 15) + 63
    n = 0x0123456789ABCDEF
    # 0x0123456789ABCDEF -> 64 bit LE - EF CD AB 89 67 45 23 01
    bb = int_to_bytes(n, 8)
    acc = 0
    i = 0
    print(bb)
    print(hex(int.from_bytes(bb, sys.byteorder)))
    assert int.from_bytes(int_to_bytes(n, 8), sys.byteorder) == n
    # for i, b in enumerate(bb):
    #     acc |= b << i * 8
    # print(hex(acc))

    s = SequenceNumber(n=6, bits=3)
    s2 = SequenceNumber(n=7, bits=3)
    for i in range(8):
        s2 = SequenceNumber(n=i, bits=3)
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

    s, s2 = SequenceNumber(n=6, bits=3), SequenceNumber(n=7, bits=3)
    print("s:", s, ", s2:", s2)
    print("s = s + 5")
    s = s + 5
    print("s:", s, ", s2:", s2)
    print("")

    s, s2 = SequenceNumber(n=6, bits=3), SequenceNumber(n=7, bits=3)
    print("s:", s, ", s2:", s2)
    print("s = 5 + s")
    s = 5 + s
    print("s:", s, ", s2:", s2)
    print("")

    # s, s2 = SequenceNumber(n = 6, bits = 3), SequenceNumber(n = 7, bits = 3)
    # print("s:", s, ", s2:", s2)
    # print("s = s + s2")
    # s = s + s2
    # print("s:", s, ", s2:", s2)
    # print("")

    # s, s2 = SequenceNumber(n = 6, bits = 3), SequenceNumber(n = 7, bits = 3)
    # print("s:", s, ", s2:", s2)
    # print("s += s2")
    # s += s2
    # print("s:", s, ", s2:", s2)
    # print("")

    s, s2 = SequenceNumber(n=6, bits=3), SequenceNumber(n=7, bits=3)
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

    print("Sub")
    print(s)
    print("s - 2")
    print(s - 2)
    print("2 - s")
    # print(2 - s)
    # Not implementing this one as seems confusing and not useful

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
    print(
        [attr for attr in dir(s) if not callable(getattr(s, attr)) and not attr.startswith("__")])
    # print(vars(s))

    ss = SequenceNumber(n=0, bits=3)
    for i in range(32):
        print(i, ss)
        # print(int(ss))
        assert i % 8 == int(ss)
        ss += 1

    s4 = SequenceNumber(n=0, bits=3)
    print("s4:", s4)
    s4 += 8
    s4 -= 10
    print(s4)
    print(bytes(s4))
    print(bytes(SequenceNumber(n=69, bits=9)))

    aa = SequenceNumber(n=3, bits=32)
    # Careful with side effect in assert
    print("aa:", aa)
    bb = aa.post_increment()
    print("aa:", aa)
    print("bb:", bb)
    # Take care not to compare SequenceNumber to int in an assert, it just fails
    assert aa == SequenceNumber(n=4, bits=32)
    assert bb == SequenceNumber(n=3, bits=32)

    print(max(aa, bb))

    z = SequenceNumber(n=60, bits=42)
    assert z != 0
    assert z != 60
    assert z == SequenceNumber(n=60, bits=42)
    # 0 == z
    # z == 0
    try:
        0 > z
    except TypeError:
        pass
    else:
        assert False
    try:
        z > 0
    except TypeError:
        pass
    else:
        assert False
    # try:
    #     z <= 0
    # except TypeError:
    #     pass
    # try:
    #     z < 0
    # except TypeError:
    #     pass
    # try:
    #     z > 0
    # except TypeError:
    #     pass
    # else:
    #     assert False
    # try:
    #     0 >= z
    # except TypeError:
    #     pass

    assert SequenceNumber(n=4, bits=4) > SequenceNumber(n=3, bits=4)
    assert SequenceNumber(n=20, bits=4) > SequenceNumber(n=3, bits=4)
    assert SequenceNumber(n=14, bits=4) < SequenceNumber(n=3, bits=4)
    assert SequenceNumber(n=20, bits=3) != SequenceNumber(n=3, bits=4)
    assert SequenceNumber(n=0, bits=4) >= SequenceNumber(n=-1, bits=4)


class A:
    pass


class B(A):
    pass


if __name__ == "__main__":
    sys.exit(main(sys.argv))
