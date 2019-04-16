#!/usr/bin/env python3

import sys
import unittest

from protocol import Packet

# Yes there is a decent amount of duplication in here but blame Python's None
# value which means I am unsure if I have accounted for every single combination
# and therefore have decided an exhaustive test is a good idea

class TestPacket(unittest.TestCase):
    def setUp(self):
        self.b = bytes([1, 2, 3])

    def test_default_construction_fails(self):
        self.assertRaises(Exception, Packet)

    def test_payload_only_construction_fails(self):
        self.assertRaises(Exception, Packet, payload = self.b)


    def test_new_connection_fails(self):
        self.assertRaises(Exception, Packet, new_connection = False, payload = self.b)
        self.assertRaises(Exception, Packet, new_connection = None, payload = self.b)
    def test_new_connection_succeeds(self):
        Packet(new_connection = True, payload = self.b)


    def test_no_sequence_number_fails(self):
        self.assertRaises(Exception, Packet, sequence_number = None, payload = self.b)
    def test_sequence_number_succeeds(self):
        Packet(sequence_number = 0, payload = self.b)
        Packet(sequence_number = 1, payload = self.b)
        Packet(sequence_number = 4294967294, payload = self.b)


    def test_none_fails(self):
        self.assertRaises(Exception, Packet, new_connection = None,
                sequence_number = None, payload = self.b)
        self.assertRaises(Exception, Packet, new_connection = False,
                sequence_number = None, payload = self.b)
    def test_new_connection_succeeds_2(self):
        Packet(new_connection = True, sequence_number = None, payload = self.b)


    def test_new_connection_with_sequence_number_zero_fails(self):
        self.assertRaises(Exception, Packet, new_connection = True,
                sequence_number = 0, payload = self.b)
        self.assertRaises(Exception, Packet, new_connection = True,
                sequence_number = 1, payload = self.b)
    def test_existing_connection_with_sequence_number_succeeds(self):
        Packet(sequence_number = 0, payload = self.b)
        Packet(sequence_number = 1, payload = self.b)
        Packet(sequence_number = 4294967294, payload = self.b)

        Packet(new_connection = None, sequence_number = 0, payload = self.b)
        Packet(new_connection = False, sequence_number = 0, payload = self.b)




def main(argv):
    unittest.main()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
