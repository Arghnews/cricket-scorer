#!/usr/bin/env python3

import sys
import struct

if sys.platform == "esp8266":
    import uos
else:
    import random

# TODO: raise more specific exceptions than Exception

# Would have made class picklable but micropython doesn't support this so just
# using to_bytes instead

class SequenceNumber(object):
    "Class wrapping 4 byte unsigned sequence numbers"

    __slots__ = ("_sequence_number")

    def __init__(self, sequence_number = None):
        pass

    def increment(self):
        if self._sequence_number == 4294967294:
            self._sequence_number = 0
        else:
            self._sequence_number = self._sequence_number + 1

    def __le__(self, other):
        return self._sequence_number <= other._sequence_number

    def __str__(self):
        pass

class Packet:
    # Cannot use sys.getsizeof as not implemented in micropython
    # _size # int - size of 4
    # _sequence_number # int size of 4
    # _new_connection_flag # bool, size of 1
    # _payload # bytes, size of len(bytes_object_instance)

    def __init__(self, *, sequence_number = None, new_connection = None,
            payload):
        if sequence_number is None and new_connection is None or \
                sequence_number is not None and new_connection is True:
            raise Exception("Packet must have exactly one of either a sequence "
                    "number or the new_connection flag set ")
        if payload is None or type(payload) is not bytes:
            raise Exception("Must provide a bytes object as payload")

        self._new_connection_flag = new_connection
        if self._new_connection_flag:
            # As of 201904 in micropython py/objint.c#L419 it seems from_bytes
            # isn't implemented correctly/fully as per the spec
            # int.from_bytes(uos.urandom(4), sys.byteorder)
            # No positional params in micropython, etc. so using struct instead
            #
            # Want to gen sequence numbers using only lower half of the bit
            # range to reduce change we ever have to actually use wrap around
            # code - still a good 2 billion ish values to pick from
            if sys.platform == "esp8266":
                random_number = struct.unpack("<I", uos.urandom(4))[0] >> 1
            else:
                random_number = random.randint(0, 2147483647)
            self._sequence_number = random_number
            assert self._sequence_number > 0 and \
                    self._sequence_number < 2147483647
        else:
            # Unsure here - pushing protocol into packet data
            # Wrap around for unsigned 4 byte.
            self._sequence_number = sequence_number + 1

        self._payload = payload

    def size(self):
        # Could make this smarter rather than hard coded as 9
        return 9 + len(self._payload)

    def to_bytes(self):
        return struct.pack("!II?", self.size(), self._sequence_number,
                self._new_connection_flag) + self._payload

    def __str__(self):
        return ("size:{}, sequence_number:{:,} , new_connection_flag:{}, "
                "payload:{}").format(self.size(), self._sequence_number,
                        self._new_connection_flag, self._payload)
        # return str(self.__class__) + ": " + str(self.__dict__)

def main(argv):
    # print("Hello world!")
    # p = Packet(new_connection = True, payload = bytes([1,2,3]))
    # print(p)
    # print(p.to_bytes())

    b = bytes([1, 2, 3])

    p1 = Packet()

    p1 = Packet(payload = b)

    p2 = Packet(new_connection = False, payload = b)
    p2 = Packet(new_connection = True, payload = b)
    p2 = Packet(new_connection = None, payload = b)

    p2 = Packet(sequence_number = None, payload = b)
    p2 = Packet(sequence_number = 0, payload = b)
    p2 = Packet(sequence_number = 1, payload = b)
    p2 = Packet(sequence_number = 4294967294, payload = b)

    p2 = Packet(new_connection = None, sequence_number = None, payload = b)
    p2 = Packet(new_connection = False, sequence_number = None, payload = b)
    p2 = Packet(new_connection = True, sequence_number = None, payload = b)

    p2 = Packet(new_connection = None, sequence_number = 0, payload = b)
    p2 = Packet(new_connection = False, sequence_number = 0, payload = b)
    p2 = Packet(new_connection = True, sequence_number = 0, payload = b)


    p2 = Packet(new_connection = None, sequence_number = 1, payload = b)
    p2 = Packet(new_connection = False, sequence_number = 1, payload = b)
    p2 = Packet(new_connection = True, sequence_number = 1, payload = b)

    p2 = Packet(new_connection = None, sequence_number = 4294967294, payload = b)
    p2 = Packet(new_connection = False, sequence_number = 4294967294, payload = b)
    p2 = Packet(new_connection = True, sequence_number = 4294967294, payload = b)



if __name__ == "__main__":
    sys.exit(main(sys.argv))
