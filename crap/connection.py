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

# FIXME: SEE THIS - Resetting the id is reasonable to do. Allows sequence number
# resets for a connection and both sides renegotiate. Better than stuff with
# sequence numbers that is going to be tough. This way "rogue packets" will
# cause the current stable connection to reset as such but that's fine, we don't
# have much state in the payload and the connection will continue.

# FIXME FIXME: think the fix is master slave type and the sender upon seeing a
# new id for the receiver generates a new one and sends that out.
# If/when the receiver receives this it sets its id to that and replies.
# The sender/master then changes its receiver_id to that one.
# This works nicely as now the receiver must temporally get and respond with new
# data that cannot be old as ids are random.
# For an old id packet that appears, this process occurs but crucially the
# sender does not change their receiver_id immediately. The "confirmation" of a
# connection change only happens when they get a reply with the new receiver_id.
# The only extra state needed is the sender must remember the receiver_id it
# just sent out to know whether to switch to it or not. And perhaps have that on
# a small timeout.

# Bit of a mess.
# Hand of to higher layers.
# Is it an issue of multiple connections on same id if they ask within
# timeframe? Suspect no as this is a single connection protocol and the receiver
# would not respond with both.
# UDP send failing on localhost is kind of annoying.
# What to do about dirty try/except blocks in udp class - mainly put there for
# quick testing anyway.

def sender2(sock, my_id = None):
    if my_id is None:
        my_id = gen_random(4)
    # Consider replacing sender with tx for transmitter and receiver with rx for
    # receiver
    rx_id = Packet.UNKNOWN_ID
    new_rx_id = Packet.UNKNOWN_ID
    gen_id_time = 0
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)
    while True:
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 0 * 1000))
        print("Received:", packet)
        if packet is None:
            # time.sleep(1)
            pass

        elif packet.sender == rx_id and packet.receiver == my_id:
            # Existing connection, packet destined for us
            if packet.sequence_number >= next_remote_seq:
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
            else:
                print("Got old/duplicate packet")

            # if valid_packet(packet):
            #     pass_to_higher_layer_reply_if_score_updated()
        # elif packet.sender == rx_id and packet.receiver == Packet.UNKNOWN_ID \
        #         and packet.id_change == Packet.UNKNOWN_ID:
        #     print("Received old discovery packet")
        elif packet.sender == new_rx_id and packet.receiver == my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
                # and packet.id_change == old_rx_id:
            # Switch connection as received what we just sent
            rx_id = new_rx_id
            new_rx_id = Packet.UNKNOWN_ID
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)
            print("Switching connection - new receiver:", rx_id)
            p = Packet(sender = my_id, receiver = rx_id,
                    sequence_number = int(next_local_seq.post_increment()))
            # print("Sending confirm changed:", p)
            # sock.send(bytes(p))
            # sock.send(bytes(p))
        # elif packet.sender == old_rx_id and packet.receiver == Packet.UNKNOWN_ID \
        #         and packet.id_change == Packet.UNKNOWN_ID:
        #     print("Received echo packet from old id - ignoring")
            # This is to prevent continual id generations when the receiver
            # changes id and then (latency allowing) an "old" packet gets
            # through just with it's id on. This will then trigger another id
            # generation event and this will continue until we accidentally trip
            # over the latency window.
            # This solution relies on the probability that the new id != old id
            # otherwise we'll forever ignore the old id.
            # Unsure if this is needed, haven't seen it yet. Ugh.
        else:
            # TODO: implement for esp
            # int(time.monotonic())
            if new_rx_id == Packet.UNKNOWN_ID or gen_id_time + 10 < int(time.monotonic()):
                # asdkjfasdjf jasdkjfasd ## See here <-
                # Some weird python scoping bullshit means new_rx_id is not
                # getting reassigined so at the print statement below it is
                # still 0
                # TODO: fix all gen_randoms with this
                new_rx_id = gen_random(4, excluding = (Packet.UNKNOWN_ID,
                    rx_id, new_rx_id))
                print("Genning new rx_id", new_rx_id)
                gen_id_time = int(time.monotonic())
            p = Packet(
                sender = my_id,
                receiver = packet.sender,
                id_change = new_rx_id)
            print("Responding with id_change packet:", p)
            print("new_rx_id =", new_rx_id)
            sock.send(bytes(p))
        print("------------------------------------------------")
        time.sleep(2)

def receiver2(sock, my_id = None):
    if my_id is None:
        my_id = gen_random(4)
    rx_id = Packet.UNKNOWN_ID
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)
    while True:
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 0 * 1000))
        print("Received:", packet)

        if packet is None: # Timed out or got garbled message
            p = Packet(sender = my_id, receiver = rx_id,
                    sequence_number = int(next_local_seq.post_increment()))
            print("Sending lookout message:", p)
            sock.send(bytes(p))

        elif packet.sender == rx_id and packet.receiver == my_id \
                and packet.id_change == Packet.UNKNOWN_ID:
            if packet.sequence_number >= next_remote_seq:
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
            else:
                print("Got old/duplicate packet")
            # if valid_packet(packet): # Check sequence number here
            #     pass_to_higher_layer_update_score(packet.data)
            #     # TODO: with what? can add complexity and reliability here
            #     reply()
        elif packet.receiver == my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            print("Changing id", my_id, "->", packet.id_change)
            p = Packet(sender = packet.id_change, receiver = packet.sender, id_change = my_id)
            my_id = packet.id_change
            rx_id = packet.sender
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)
            print("Sending back details:", p)
            sock.send(bytes(p))
        else:
            # Stamp sender == my_id and leave receiver
            p = Packet(sender = my_id, receiver = Packet.UNKNOWN_ID)
            # p = Packet(sender = my_id, receiver = packet.sender)
            print("Got unknown sending back my details:", p)
            sock.send(bytes(p))
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
