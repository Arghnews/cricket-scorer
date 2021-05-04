#!/usr/bin/env micropython

import sys

from .utility import gen_random, int_to_bytes
from .sequence_numbers import SequenceNumber

# Would like to assert sequence_number length.
# Thinking about creating some kind of fixed size int class.
# ie. class FixedSizeInt(int): def self __len__(self): return self._len

class Packet:

    UNKNOWN_ID = 0

    ID_SIZE = 4
    SEQUENCE_NUMBER_SIZE = 4
    # This tight coupling sucks - maybe some kind of factory to fix, lot of work
    PAYLOAD_SIZE = 9

    # MAXIMUM_PAYLOAD_SIZE = 9

    # https://stackoverflow.com/a/32720603
    # Micropython class objects do not seem to have this mappingproxy object
    # called "__dict__" for accessing class attributes.
    # Would've used.
    # return sum(v for k, v in cls.__dict__.items() if k.isupper() and k.endswith("_SIZE"))
    @classmethod
    def packet_size(cls):
        return cls.ID_SIZE * 3 + cls.SEQUENCE_NUMBER_SIZE + cls.PAYLOAD_SIZE
        # return sum(getattr(cls, x) for x in dir(cls) if x.isupper()
        #         and x.endswith("_SIZE") and type(getattr(cls, x)) is int)

    @classmethod
    def payload_as_string(cls, payload):
        return " ".join("{:02X}".format(x) for x in payload)

    def __str__(self):
        # Don't use {:,} for sequence number, it tries to use it as int or some
        # such
        return "{{{:,} {:,} {:,} {} - {}}}".format(self.sender, self.receiver,
                self.id_change, self.sequence_number,
                Packet.payload_as_string(self.payload))

    def __init__(self, *, sender, receiver, id_change = 0,
            sequence_number = SequenceNumber(n = 0,
                bytes_ = SEQUENCE_NUMBER_SIZE), payload = bytes(PAYLOAD_SIZE)):

        cls = type(self)
        assert sender < 2 ** (cls.ID_SIZE * 8)
        assert receiver < 2 ** (cls.ID_SIZE * 8)
        assert id_change < 2 ** (cls.ID_SIZE * 8)
        assert type(sequence_number) is SequenceNumber
        assert sequence_number.__int__() < 2 ** (cls.SEQUENCE_NUMBER_SIZE * 8)
        assert type(payload) is bytes
        assert len(payload) is cls.PAYLOAD_SIZE

        self.sender = sender
        self.receiver = receiver
        self.id_change = id_change
        self.sequence_number = sequence_number
        self.payload = payload

    def __bytes__(self):
        cls = type(self)
        ba = bytearray()
        ba += int_to_bytes(self.sender, cls.ID_SIZE)
        ba += int_to_bytes(self.receiver, cls.ID_SIZE)
        ba += int_to_bytes(self.id_change, cls.ID_SIZE)
        ba += int_to_bytes(self.sequence_number.__int__(),
                cls.SEQUENCE_NUMBER_SIZE)
        ba += self.payload
        return bytes(ba)

    @classmethod
    def from_bytes(cls, bytes_):
        # print("Received in from_bytes:", bytes_)
        if bytes_ is None:
            return None
        assert len(bytes_) == Packet.packet_size()
        # Holy lack of DRY batman. This is so error prone, I hate it.
        offsets = offset_slices(bytes_, cls.ID_SIZE, cls.ID_SIZE,
                cls.ID_SIZE, cls.SEQUENCE_NUMBER_SIZE, cls.PAYLOAD_SIZE)
        val = lambda: next(offsets)
        packet = Packet(
                sender = int.from_bytes(val(), sys.byteorder),
                receiver = int.from_bytes(val(), sys.byteorder),
                id_change = int.from_bytes(val(), sys.byteorder),
                sequence_number = SequenceNumber(
                    int.from_bytes(val(), sys.byteorder),
                    bytes_ = cls.SEQUENCE_NUMBER_SIZE),
                payload = val())
        try:
            val()
        except StopIteration:
            pass
        else:
            assert False, "Should've raised StopIteration, byte offsets don't "
            "consume all of input"
        return packet

    def __eq__(self, other):
        if type(other) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

def offset_slices(bytes_, *offsets):
    assert sum(offsets) == len(bytes_)
    acc = 0
    for offset in offsets:
        yield bytes_[acc:acc + offset]
        acc += offset

def same(self, other, *attrs):
    return all(getattr(self, attr) == getattr(other, attr) for attr in attrs)

li = 0

def f():
    global li
    print(li)
    li += 1
    return li

def args(*args):
    pass

def main(argv):
    args(f(), f(), f(), f())

    offsets = offset_slices(range(25), 4, 4, 4, 4, 9)
    print(list(next(offsets)))
    print(list(next(offsets)))
    print(list(next(offsets)))
    print(list(next(offsets)))
    print(list(next(offsets)))

#     sn = SequenceNumber(n = 5, bits = 32)
#     p1 = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
#             sequence_number = sn, ack = False, payload = bytes(range(9)))
#     print(Packet.packet_size())

#     sn2 = SequenceNumber(n = 5, bits = 32)

#     p2 = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
#             sequence_number = sn2, ack = False, payload = bytes(range(9)))

# #     # No vars in micropython
# #     print(vars(p1))
# #     print(vars(p2))
# #     print(vars(p1) == vars(p2))
# #     print("my_vars:", p1.__dict__)
# #     print([attr for attr in dir(p1) if not callable(getattr(p1, attr)) and not attr.startswith("__")])
# #     print(vars(p1))
# #     print(same(p1, p2))
# #     return

#     print("Hello world!")

#     payload = bytes(range(9))

#     # print(bytes(sn))
#     # return

#     p = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
#             sequence_number = sn, ack = False, payload = payload)
#             # payload = bytes([1,2,3]))
#     print(p)
#     data = bytes(p)
#     print(data)

#     packet = Packet.from_bytes(data)

#     print("packet:", packet)
#     print("p:", p)
#     assert packet == p

if __name__ == "__main__":
    sys.exit(main(sys.argv))
