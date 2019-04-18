#!/usr/bin/env python3

import sys

from utility import gen_random, int_to_bytes
from sequence_numbers import SequenceNumber

class Packet:

    def __init__(self, *, connection_id = None, ack = False, sequence_number,
            payload):
        if connection_id is None:
            connection_id = gen_random(4)

        assert type(connection_id) is int
        assert connection_id < 2 ** 32
        assert len(bytes(sequence_number)) == 4
        assert type(ack) is bool
        assert type(payload) is bytes
        assert len(payload) < 2 ** 7 # 2 ** 7 not 8, first bit used as ack bit

        self.connection_id = connection_id
        self.sequence_number = sequence_number
        self.ack = ack
        self.payload = payload

    def __bytes__(self):
        ba = bytearray()
        ba.append(len(self.payload) | (self.ack << 7)) # 1 byte
        ba += int_to_bytes(self.connection_id, 32) # 4 bytes
        ba += bytes(self.sequence_number) # 4 bytes
        ba += self.payload
        return bytes(ba)

def main(argv):
    print("Hello world!")
    sn = SequenceNumber(n = 0, bits = 32)
    p = Packet(connection_id = (1 << 31) + (1 << 24) + (1 << 16) + (1 << 8) + (1 << 4),
            sequence_number = sn, payload = bytes([1,2,3]), ack = False)
    print(bytes(p))

if __name__ == "__main__":
    sys.exit(main(sys.argv))
