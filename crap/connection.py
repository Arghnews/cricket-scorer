#!/usr/bin/env python3

import sys
import time

# Sender - controller
# Sends score:
#   On startup
#   On score update
#   In response to receiving wrong score
#   On receive of packet with unknown connection id, sends score setting ack bit
#   set on current connection id
#   [Optional] If not received echoed score back after some time near RTT or
#   simply say 1-2 seconds
#
# Receiver - scoreboard
# Sends score:
#   Periodically
#   On receiving a new score
#   On startup
#   On receive of packet with unknown connection id, setting ack bit
#
#
# New connection plan v1.
# S is sender's connection id, R is receiver's initial connection id
#
# R receives packet with [id: != R, ack: False], sends [id: R, ack: True]
# S receives packet with [id: != S, ack: True], sends [id: S, ack: True]
# R now switches its active connection id to S
#
# S receives packet with [id: != S, ack: False], goto above
#
#
# This back and forth is to try and mitigate old packets hanging around the
# network causing incorrect connection switches
# This is done by requiring the sender to produce a packet with the ack bit set

# def bla(sock):
#     packet, payload_size = Packet.from_bytes(Packet.header_size())
#     payload = sock.recv(payload_size)
#     return packet,

# FIXME: think about how the sender should acquire the receiver's next sequence
# number (ie. remote sequence number for sender) after a connection switch.
# Options that immediately come to mind:
#   Sender can just ignore receiver sequence number
#   Sender remembers recently joined connection and/or remote sequence numbers
#   near 0 or just accepts the next one? With possible timeout

# TODO/FIXME/read this
# Fix the above
# Functionalise shit as this is a copy paste mess atm
# In line with the above/before it, sequence numbers all fucked atm, unsure if
# confusing remote and local or what but only see 3<3, 4<4 all the time, try
# starting one side's numbers much higher like at 1000 or something to see.
# And moar. But hey at least this first bit kinda works it seems ish

from udp_receive import SimpleUDP
from sequence_numbers import SequenceNumber
from packet import Packet
from utility import gen_random

def receiver():
    with SimpleUDP(2520, "127.0.0.1", 2521) as sock:
        connection_id = 0
        sequence_number = SequenceNumber(n = 0, bits = 32)
        remote_sequence_number = SequenceNumber(n = 0, bits = 32)

        while True:
            print("Connection id:", connection_id)
            packet = Packet.from_bytes(sock.recv(Packet.packet_size(),
                timeout_ms = 5000))
            if packet is not None:
                print("Read packet from socket:", packet)
                if packet.connection_id != connection_id:
                    # New connection
                    print("Received packet with different connection id:",
                            packet.connection_id, "to current:", connection_id)
                    if not packet.ack:
                        reply = Packet(ack = True,
                            connection_id = connection_id,
                            # TODO: change seq num here to default
                                sequence_number = sequence_number,
                                payload = bytes(9))
                        print("Sending back connection change "
                                "(ack bit set) packet:", reply)
                        # We have found new connection
                        # Send packet asking for confirm
                        sock.send(bytes(reply))
                    else:
                        print("Switching to new connection id:",
                                packet.connection_id, "from", connection_id,
                                "and setting local sequence number to 0")
                        connection_id = packet.connection_id
                        remote_sequence_number = packet.sequence_number - 1
                        sequence_number = SequenceNumber(n = 0, bits = 32)

                        print("Received data:", packet.payload)

                        reply = Packet(ack = False,
                                connection_id = connection_id,
                                sequence_number = sequence_number,
                                payload = packet.payload)
                        print("Sending back echo:", reply)
                        sock.send(bytes(reply))
                        print("Incrementing sequence number")
                        sequence_number += 1

                else:
                    # Existing connection
                    if packet.ack:
                        print("Received packet with ack set on same connection")
                    if packet.sequence_number > remote_sequence_number:
                        # New data, not duplicate or old
                        remote_sequence_number = packet.sequence_number
                        print("Received new packet with sequence_number",
                                packet.sequence_number)

                        print("Received data:", packet.payload)

                        reply = Packet(ack = False,
                                connection_id = connection_id,
                                sequence_number = sequence_number,
                                payload = packet.payload)
                        print("Sending back echo:", reply)
                        sock.send(bytes(reply))
                        print("Incrementing sequence number")
                        sequence_number += 1
                    else:
                        print("Rejecting packet with older sequence " + \
                                "number ({} < {})".format(packet.sequence_number,
                                        remote_sequence_number))

                        print(packet.payload)
            else:
                print("Read None from socket")

                reply = Packet(ack = False,
                        connection_id = connection_id,
                        sequence_number = sequence_number,
                        payload = bytes(9))
                print("Sending periodic discovery packet:", reply)
                sock.send(bytes(reply))
                print("Incrementing sequence number")
                sequence_number += 1

            print("")

def sender():
    with SimpleUDP(2521, "127.0.0.1", 2520) as sock:
        connection_id = gen_random(4)
        sequence_number = SequenceNumber(n = 0, bits = 32)
        remote_sequence_number = SequenceNumber(n = 0, bits = 32)
        payload = bytes(range(9))
        while True:
            print("Connection id:", connection_id)
            packet = Packet.from_bytes(sock.recv(Packet.packet_size(),
                timeout_ms = 4000))
            if packet is None:
                print("Read None from socket")
            else:
                print("Read packet from socket:", packet)
                if packet.ack:
                    print("Got packet with ack, setting ack for reply")
                    reply = Packet(ack = True,
                            connection_id = connection_id,
                            sequence_number = sequence_number,
                            payload = payload)
                    print("Sending ack connection change reply:", reply)
                    sock.send(bytes(reply))
                    print("Incrementing sequence number")
                    sequence_number += 1
                else:
                    will_reply = False
                    if packet.sequence_number > remote_sequence_number:
                        remote_sequence_number = packet.sequence_number
                        print("Received packet with sequence_number",
                                packet.sequence_number)
                        # will_reply = True
                    if connection_id != packet.connection_id:
                        print("Received packet with different connection id:",
                                packet.connection_id, "to current:", connection_id)
                        will_reply = True

                    if will_reply:
                        print("Received data:", packet.payload)

                        reply = Packet(ack = False,
                                connection_id = connection_id,
                                sequence_number = sequence_number,
                                payload = payload)
                        print("Sending back update:", reply)
                        sock.send(bytes(reply))
                        print("Incrementing sequence number")
                        sequence_number += 1
                    else:
                        print("Rejecting packet with older sequence " + \
                                "number ({} < {})".format(packet.sequence_number,
                                        remote_sequence_number))

                        print(packet.payload)
            print("")

def main(argv):
    if len(argv) > 1:
        print("Receiver")
        receiver()
    else:
        print("Sender")
        sender()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
