#!/usr/bin/env python3

import sys

from utility import gen_random, int_to_bytes
from sequence_numbers import SequenceNumber

# header_data = connection.recv(Packet.header_size())
# header = Header(header_data)
# data = connection.recv(header.payload_size())

# Bit messy but unsure how to decouple header and payload neatly

class Packet:

    CONNECTION_ID_SIZE = 4
    SEQUENCE_NUMBER_SIZE = 4
    MAXIMUM_PAYLOAD_SIZE = 127

    @classmethod
    def header_size(cls):
        return 1 + cls.CONNECTION_ID_SIZE + cls.SEQUENCE_NUMBER_SIZE

    def __str__(self):
        return ("connection_id: {:,} , ack bit: {}, sequence_number: {}, "
                "payload: {}").format(self.connection_id, self.ack,
                        self.sequence_number, self.payload)

    def __init__(self, *, connection_id = None, ack = False,
            payload = None, sequence_number):
        cls = type(self)
        if connection_id is None:
            connection_id = gen_random(cls.CONNECTION_ID_SIZE)

        assert type(connection_id) is int
        assert connection_id < 2 ** (cls.CONNECTION_ID_SIZE * 8)
        assert type(sequence_number) is SequenceNumber
        assert len(bytes(sequence_number)) == cls.SEQUENCE_NUMBER_SIZE
        assert type(ack) is bool

        self.connection_id = connection_id
        self.sequence_number = sequence_number
        self.ack = ack
        if payload is not None:
            cls.check_payload(payload)
        self.payload = payload

    @classmethod
    def check_payload(cls, payload):
        assert type(payload) is bytes
        assert len(payload) <= cls.MAXIMUM_PAYLOAD_SIZE

    def set_payload(self, payload):
        type(self).check_payload(payload)
        self.payload = payload
        return self

    def __bytes__(self):
        # Must have a valid payload to convert to bytes
        type(self).check_payload(self.payload)

        cls = type(self)
        ba = bytearray()
        ba.append(len(self.payload) | (self.ack << 7)) # 1 byte
        ba += int_to_bytes(self.connection_id, cls.CONNECTION_ID_SIZE)
        ba += bytes(self.sequence_number)

        # print(len(ba))
        # print(cls.header_size())
        assert len(ba) == cls.header_size()

        ba += self.payload
        return bytes(ba)

    @classmethod
    def from_bytes(cls, bytes_):
        """Parses bytes as a Packet (header)
        Returns a header (with null payload) and the size of the payload to
        read next"""
        assert len(bytes_) == cls.header_size()

        # First byte
        ack = bool(bytes_[0] & (1 << 7))
        payload_size = bytes_[0] & ~(1 << 7)
        offset = 1

        # If keeping these lines this should be neatened somehow, manual offset
        # is far too error-prone
        connection_id = int.from_bytes(
                bytes_[offset:offset + cls.CONNECTION_ID_SIZE], sys.byteorder)
        offset += cls.CONNECTION_ID_SIZE

        # TODO: change this when change SequenceNumber to bytes from bits
        sequence_number = SequenceNumber(
                n = bytes_[offset:offset + cls.SEQUENCE_NUMBER_SIZE],
                bits = cls.SEQUENCE_NUMBER_SIZE * 8)

        # print(offset, offset + cls.SEQUENCE_NUMBER_SIZE)
        # print(sequence_number)
        offset += cls.SEQUENCE_NUMBER_SIZE

        packet = cls(connection_id = connection_id, ack = ack,
                sequence_number = sequence_number)

        return packet, payload_size

    def __eq__(self, other):
        if type(other) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

def same(self, other, *attrs):
    return all(getattr(self, attr) == getattr(other, attr) for attr in attrs)

def main(argv):

    sn = SequenceNumber(n = 5, bits = 32)
    sn2 = SequenceNumber(n = 5, bits = 32)

    p1 = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
            sequence_number = sn, ack = False)
    p2 = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
            sequence_number = sn2, ack = False)

#     # No vars in micropython
#     print(vars(p1))
#     print(vars(p2))
#     print(vars(p1) == vars(p2))
#     print("my_vars:", p1.__dict__)
#     print([attr for attr in dir(p1) if not callable(getattr(p1, attr)) and not attr.startswith("__")])
#     print(vars(p1))
#     print(same(p1, p2))
#     return

    print("Hello world!")

    payload = bytes(range(7))

    # print(bytes(sn))
    # return

    p = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
            sequence_number = sn, ack = False)
            # payload = bytes([1,2,3]))
    p.set_payload(payload)
    print(p)
    data = bytes(p)
    print(data)

    packet, payload_size = Packet.from_bytes(data[:Packet.header_size()])

    print("Packet:", packet)
    print("payload_size is", payload_size)
    assert payload_size == len(payload)
    assert p != packet
    assert p == packet.set_payload(payload)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
