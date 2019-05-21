#!/usr/bin/env micropython
#!/usr/bin/env python3

# Untested on actual esp atm.
# Also still need to implement (really trying to think of a neat way) to
# implement the wrapper to let the data go in. I feel like the answer is somehow
# a coroutine but can't quite put my mental finger on how it will work.
# Also think about the EVIL try/except blocks that are in udp_receive for now...

# One thing to work on is the notion of being disconnected. Unconnected
# (initial) state is trivial, but to work out when disconnected is trickier but
# would be useful to stop sending loads of messages into the void.

# To note: in the case of receiving a burst of wrong score packets we respond to
# every single one - potentially flooding the medium. If say when we then change
# score immediately after sending the burst, all the echoes/acks from the
# receiver will then also be wrong, causing us to respond to each and every one
# of those with a response (that will also all be acked). This could continue
# until all messages are received and the score stops changing in less than the
# RTT. Potential solution: some kind of timeout on the sender side to prevent
# resending the same score over and over within a timeframe. If the score is
# continually changing then sending the new score is fine as we do want the
# update as fast as possible and we don't anticipate continuous changes with
# very little gap between them.
# All these arbitrary timeouts really suck. Perhaps try to shift some or all to
# depend on RTT somewhat. But then we need packets to contain ack data so we
# know if we send 2 packets which is being acked.
#
# Note also - on x86 micropython the random seeds are the same and so the id's
# generated for both sender and receiver are the same. I did not plan for this
# but by happy coincidence and when thought about this is no issue.
#

import sys
import time

from udp_receive import SimpleUDP
from sequence_numbers import SequenceNumber
from packet import Packet
from utility import gen_random, int_to_bytes, probability
from countdown_timer import make_countdown_timer

def sender2(sock, my_id = None):

    # TODO now: immediately when connected send score

    if my_id is None:
        my_id = gen_random(4, excluding = Packet.UNKNOWN_ID)
        print("Initial id:", my_id)
    rx_id = Packet.UNKNOWN_ID
    new_rx_id = Packet.UNKNOWN_ID
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)

    new_connection_countdown = make_countdown_timer(seconds = 10,
            started = False)

    last_received_timer = make_countdown_timer(seconds = 15, started = False)
    connected = False

    resend_same_countdown = make_countdown_timer(seconds = 0.5, started = True)
    # We use this to identify sending "same packet" again
    last_payload_sent = None

    score = latest_score()
    # latest_remote_score = None

    # TODO: add initial send on startup

    while True:

        # print("Packet size:", Packet.packet_size())
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 4000))
        print("Received:", packet)
        old_score = score
        score = latest_score()

        if new_connection_countdown.just_expired():
            print("New connection reply window expired, resetting new_rx_id")
            new_rx_id = Packet.UNKNOWN_ID
        if last_received_timer.just_expired():
            print("Disconnected")
            connected = False
            # Reset everything
            rx_id = Packet.UNKNOWN_ID
            new_rx_id = Packet.UNKNOWN_ID
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)

        if packet is None:
            if connected and old_score != score:
                p = Packet(sender = my_id, receiver = rx_id,
                        sequence_number = next_local_seq.post_increment(),
                        payload = score)
                sock.send(p.__bytes__())
                last_payload_sent = p.payload
                print("Sending new score")

        elif packet.sender == rx_id and packet.receiver == my_id:
            if packet.sequence_number >= next_remote_seq:
                last_received_timer.reset()
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
                if packet.payload != score:
                    print("GOT WRONG SCORE ----------------------------------")
                    assert type(packet.payload) is bytes and \
                            len(packet.payload) == Packet.PAYLOAD_SIZE
                    if score != last_payload_sent or \
                            resend_same_countdown.just_expired():
                        p = Packet(sender = my_id, receiver = rx_id,
                                sequence_number = next_local_seq.post_increment(),
                                payload = score)
                        print("Sending response data packet", p)
                        sock.send(p.__bytes__())
                        last_payload_sent = p.payload
                        resend_same_countdown.reset()
                    else:
                        print("Not sending updated score as would be duplicate "
                        "within timeout")
            else:
                print("Got old/duplicate packet")

        elif packet.sender == rx_id and packet.receiver == Packet.UNKNOWN_ID:
            # If we don't we force a re-change of connection on receiving old
            # packets from the current connection that has just been changed to
            print("Got old discovery packet from current receiver - ignoring")
            # print("AJKSDHFJASDHF\n\n\n\nasdfjkadskfjkasdjfjasdkj\n\n\nasdkfjas")
            pass

        elif packet.sender == new_rx_id and packet.receiver == my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            rx_id = new_rx_id
            new_rx_id = Packet.UNKNOWN_ID
            next_remote_seq = SequenceNumber(bytes_ = 4)
            next_local_seq = SequenceNumber(bytes_ = 4)
            new_connection_countdown.stop()
            print("Switching connection - new receiver:", rx_id)
            # This is not a control packet - we have no way to differentiate
            # (currently) this as one. So put the correct updated score in here
            p = Packet(sender = my_id, receiver = rx_id,
                    sequence_number = next_local_seq.post_increment(),
                    payload = score)
            print("Sending score", p)
            sock.send(p.__bytes__())
            connected = True
            last_received_timer.reset()
            last_payload_sent = None

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
            last_payload_sent = None

        print("------------------------------------------------")

def receiver2(sock, my_id = None):
    if my_id is None:
        my_id = gen_random(4, excluding = Packet.UNKNOWN_ID)
        print("Initial id:", my_id)
    rx_id = Packet.UNKNOWN_ID
    next_remote_seq = SequenceNumber(bytes_ = 4)
    next_local_seq = SequenceNumber(bytes_ = 4)
    lookout_timeout = make_countdown_timer(seconds = 5, started = True)
    score = bytes(9)

    while True:
        packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 3000))
        if packet is not None:
            print("Received:", packet)

        if packet is None: # Timed out or got garbled message
            print("None")
            if lookout_timeout.just_expired():
                lookout_timeout.reset()
                p = Packet(sender = my_id, receiver = rx_id,
                        sequence_number = next_local_seq.post_increment(),
                        payload = score)
                print("Sending lookout message:", p)
                sock.send(p.__bytes__())

        elif packet.sender == rx_id and packet.receiver == my_id \
                and packet.id_change == Packet.UNKNOWN_ID:
            if packet.sequence_number >= next_remote_seq:
                next_remote_seq = packet.sequence_number + 1
                print("Got good packet")
                if packet.payload != score:
                    score = packet.payload
                    if probability(0.2, True, False):
                        print("Setting wrong score for testing")
                        # For testing, set wrong score
                        score = int_to_bytes(-1, 9)
                    p = Packet(sender = my_id, receiver = rx_id,
                            sequence_number = next_local_seq.post_increment(),
                            payload = score)
                    print("Updating score to", int.from_bytes(score,
                        sys.byteorder), "and echoing back", p)
                    sock.send(p.__bytes__())
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
        time.sleep(0.1)

latest_score_score = 0
def latest_score():
    global latest_score_score
    # Micropython has no user defined attribs on funcs
    # https://docs.micropython.org/en/latest/genrst/core_language.html#user-defined-attributes-for-functions-are-not-supported
    if probability(0.20, True, False):
        latest_score_score += 1
        print("Latest score increased to", latest_score_score)
    return int_to_bytes(latest_score_score, 9)

def main(argv):

    if len(argv) > 1:
        print("Receiver")
        previous_lookout_msg = make_countdown_timer(seconds = 5)
        with SimpleUDP(2520, "127.0.0.1", 2521) as sock:
            receiver2(sock)

    else:
        # Problem atm is how to send stuff and receive and know stuff.
        print("Sender")
        with SimpleUDP(2521, "127.0.0.1", 2520) as sock:
            sender2(sock)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
