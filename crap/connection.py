#!/usr/bin/env micropython
# !/usr/bin/env python3

# Untested on actual esp atm.
# Also still need to implement (really trying to think of a neat way) to
# implement the wrapper to let the data go in. I feel like the answer is somehow
# a coroutine but can't quite put my mental finger on how it will work.
# Also think about the EVIL try/except blocks that are in udp_receive for now...

import sys
import time

from udp_receive import SimpleUDP
from sequence_numbers import SequenceNumber
from packet import Packet
from utility import gen_random
from countdown_timer import make_countdown_timer

def sender2(sock, my_id = None):
    if my_id is None:
        my_id = gen_random(4, excluding = Packet.UNKNOWN_ID)
    rx_id = Packet.UNKNOWN_ID
    new_rx_id = Packet.UNKNOWN_ID
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)
    new_connection_countdown = make_countdown_timer(seconds = 10)

    while True:
        # print("Packet size:", Packet.packet_size())
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 0 * 1000))
        print("Received:", packet)

        if new_connection_countdown.just_expired():
            print("New connection reply window expired, resetting new_rx_id")
            new_rx_id = Packet.UNKNOWN_ID

        if packet is None:
            # time.sleep(1)
            pass

        elif packet.sender == rx_id and packet.receiver == my_id:
            if packet.sequence_number >= next_remote_seq:
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
            else:
                print("Got old/duplicate packet")

        elif packet.sender == new_rx_id and packet.receiver == my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            rx_id = new_rx_id
            new_rx_id = Packet.UNKNOWN_ID
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)
            new_connection_countdown.stop()
            print("Switching connection - new receiver:", rx_id)
            p = Packet(sender = my_id, receiver = rx_id,
                    sequence_number = next_local_seq.post_increment())
        else:
            if new_rx_id == Packet.UNKNOWN_ID:
                new_connection_countdown.reset()
                new_rx_id = gen_random(4, excluding = (Packet.UNKNOWN_ID,
                    rx_id, new_rx_id))
                print("Genning new rx_id", new_rx_id)
            p = Packet(
                sender = my_id,
                receiver = packet.sender,
                id_change = new_rx_id)
            print("Responding with id_change packet:", p)
            print("new_rx_id =", new_rx_id)
            sock.send(p.__bytes__())
        print("------------------------------------------------")
        time.sleep(2)

def receiver2(sock, my_id = None):
    if my_id is None:
        my_id = gen_random(4, excluding = Packet.UNKNOWN_ID)
    rx_id = Packet.UNKNOWN_ID
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)
    while True:
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 0 * 1000))
        print("Received:", packet)

        if packet is None: # Timed out or got garbled message
            p = Packet(sender = my_id, receiver = rx_id,
                    sequence_number = next_local_seq.post_increment())
            print("Sending lookout message:", p)
            sock.send(p.__bytes__())

        elif packet.sender == rx_id and packet.receiver == my_id \
                and packet.id_change == Packet.UNKNOWN_ID:
            if packet.sequence_number >= next_remote_seq:
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
            else:
                print("Got old/duplicate packet")
        elif packet.receiver == my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            print("Changing id", my_id, "->", packet.id_change)
            p = Packet(sender = packet.id_change, receiver = packet.sender, id_change = my_id)
            my_id = packet.id_change
            rx_id = packet.sender
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)
            print("Sending back details:", p)
            sock.send(p.__bytes__())
        else:
            p = Packet(sender = my_id, receiver = Packet.UNKNOWN_ID)
            print("Got unknown sending back my details:", p)
            sock.send(p.__bytes__())
        print("------------------------------------------------")
        time.sleep(2)

def main(argv):
    if len(argv) > 1:
        print("Receiver")
        with SimpleUDP(2520, "127.0.0.1", 2521) as sock:
            # while True:
            #     print(sock.recv(9, timeout_ms = 1 * 1000))
            receiver2(sock)
    else:
        print("Sender")
        with SimpleUDP(2521, "127.0.0.1", 2520) as sock:
            # while True:
            #     sock.send(bytes(range(9)))
                # time.sleep(1)
            sender2(sock)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
