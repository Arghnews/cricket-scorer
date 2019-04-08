#!/usr/bin/env python3

import sys
import unittest

from protocol import Packet

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



def main(argv):
    unittest.main()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
