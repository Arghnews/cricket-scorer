#!/usr/bin/env python3
#!/usr/bin/env micropython

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

# TODO: haven't changed it for now during refactoring - but can we merge the
# receiver else case where it sends a sender = my_id and receiver =
# Packet.UNKNOWN_ID together with the standard case where we send the score?
# Looking at sender case I assume this would trigger either one of two cases:
# If already connected then this packet would appear like any other
# reply/lookout packet
# If either the sender or the receiver are not what the sender expects then it
# will go through the connection change/switching procedure

import time
import sys

from .udp_receive import SimpleUDP
from .sequence_numbers import SequenceNumber
from .packet import Packet
from .utility import gen_random, int_to_bytes, probability
from .countdown_timer import make_countdown_timer

# class BaseConnection:
#     sock
#     my_id
#     rx_id
#     next_remote_seq
#     next_local_seq

#     def reset(*, rx_id = None, my_id = None): pass # new_rx_id
#     def send_data(payload): pass
#     def recv(timeout_ms): pass

#     # Sender - else response to lookout msg
#     p = Packet(
#         sender = my_id,
#         receiver = packet.sender,
#         id_change = new_rx_id)

#     # Receiver - on connection switch
#     # Packet(my_id, rx_id, old_my_id)
#     p = Packet(sender = packet.id_change, receiver = packet.sender, id_change = my_id)

#     # Receiver - on receiving unknown
#     p = Packet(sender = my_id, receiver = Packet.UNKNOWN_ID)

class BaseConnection:

    def __init__(self, sock, log, my_id = None, rx_id = Packet.UNKNOWN_ID,
            next_remote_seq = SequenceNumber(
                bytes_ = Packet.SEQUENCE_NUMBER_SIZE),
            next_local_seq = SequenceNumber(
                bytes_ = Packet.SEQUENCE_NUMBER_SIZE)):
        if my_id is None:
            my_id = gen_random(Packet.ID_SIZE, excluding = Packet.UNKNOWN_ID)

        self.sock = sock
        self.my_id = my_id
        self.rx_id = rx_id
        self.next_remote_seq = next_remote_seq
        self.next_local_seq = next_local_seq
        self.log = log

    def recvfrom(self, timeout_ms):
        data, addr = self.sock.recvfrom(Packet.packet_size(),
                timeout_ms = timeout_ms)
        if data is not None and len(data) != Packet.packet_size():
            self.log.error("Received wrong packet size, logging and discarding. Packet:", data)
            return None, None
        return Packet.from_bytes(data), addr

    def sendto(self, payload, addr):
        # print("Sending response data packet", packet)
        packet = Packet(sender = self.my_id, receiver = self.rx_id,
                sequence_number = self.next_local_seq.post_increment(),
                payload = payload)
        self.log.debug("Sending:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    # Sender only
    def send_id_change_response(self, id_change_packet, new_rx_id, addr):
        packet = Packet(sender = self.my_id,
                receiver = id_change_packet.sender, id_change = new_rx_id,
                payload = int_to_bytes(-1, Packet.PAYLOAD_SIZE))
        self.log.debug("Sending:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    # Receiver only
    def change_and_send_connection_change(self, id_change_packet, addr):
        old_my_id = self.my_id
        self.reset(my_id = id_change_packet.id_change,
                rx_id = id_change_packet.sender)
        packet = Packet(sender = id_change_packet.id_change,
                receiver = id_change_packet.sender, id_change = old_my_id,
                payload = int_to_bytes(-1, Packet.PAYLOAD_SIZE))
        self.log.debug("Sending:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    def reset(self, *, my_id = None, rx_id = Packet.UNKNOWN_ID):
        if my_id is not None:
            self.my_id = my_id
        self.rx_id = rx_id
        self.next_remote_seq = SequenceNumber(
                bytes_ = Packet.SEQUENCE_NUMBER_SIZE)
        self.next_local_seq = SequenceNumber(
                bytes_ = Packet.SEQUENCE_NUMBER_SIZE)

# We have a lot of (well - exclusively) hard coded timeouts
#
# Don't have:
#   Any way to tell latency (and therefore respond to it)
#   Any way to tell packet drop rate (and therefore respond to it)
#       From this any kind of way to react to the medium dropping - usually
#       congestion control is in here but for this at least obviously there is
#       none as it's just us
#
#   Thoughts on how to genericise
# We know there are only 3 kinds of packet, and 2 per sender and 2 per receiver
# (1 shared type)

#  async def sender_loop(args):
    #  log = args.logger()

    #  log.info("\n\nSender started with params", args)

    #  log.debug("Initialising socket")
    #  async with args.sock(log) as sock:
        #  await f()
        #  #  got = None
        #  #  while True:
            #  #  got = (yield got)
            #  #  print("got", got)
        #  #  sender_loop_impl(sock, log, args)
            #  #  await impl(sock, log, args)

#  async def f():
    #  got = None
    #  while True:
        #  got = (yield got)
        #  print("got", got)

#  async def impl(sock, logs, args):
    #  got = None
    #  while True:
        #  got = (yield got)
        #  print("got", got)

class Sender:
    def __init__(self, args):
        self.log = args.logger

        self.log.info("\n\nSender started with params", args)

        self.log.debug("Initialising socket")
        self.sock: SimpleUDP = args.sock

        self.log.debug("Initialising connection object")
        self.conn = BaseConnection(self.sock, self.log)

        self.new_rx_id = Packet.UNKNOWN_ID

        self.lookout_timer = make_countdown_timer(
                seconds = args.lookout_timeout_seconds, started = True)

        self.new_connection_id_countdown = make_countdown_timer(
                seconds = args.new_connection_id_countdown_seconds,
                started = False)

        self.last_received_timer = make_countdown_timer(
                seconds = args.last_received_timer_seconds, started = False)
        self.connected = False

        self.resend_same_countdown = make_countdown_timer(
                seconds = args.resend_same_countdown_seconds, started = True)

        self.last_payload_sent = None

        self.score = None

        self.receiver_ip_port = args.receiver_ip_port

    def _send(self):
        assert self.score is not None, "Must poll before sending score"
        self.log.info("Sending score:", Packet.payload_as_string(self.score))
        self.conn.sendto(self.score, self.receiver_ip_port)
        self.last_payload_sent = self.score

    def poll(self, score: bytes):
        if self.score != score:
            old_score = self.score
            self.score = score

            self.log.info("Score changed from",
                    Packet.payload_as_string(old_score)
                        if old_score is not None else "no prior score",
                    "to", Packet.payload_as_string(self.score),
                    "- sending new score")
            self._send()
            self.last_payload_sent = self.score
            self.lookout_timer.reset()

        while self._poll():
            pass

    def _poll(self):
        packet, addr = self.conn.recvfrom(timeout_ms = 0)
        if addr is not None and addr != self.receiver_ip_port:
            self.log.warning("Received packet from", addr, "unexpected",
                    self.receiver_ip_port)

        if packet is not None:
            self.log.info("Received:", packet)

        # Read score would have been here

        if self.new_connection_id_countdown.just_expired():
            self.log.info("New connection reply window expired, resetting "
                    "new_rx_id")
            self.new_rx_id = Packet.UNKNOWN_ID
        if self.last_received_timer.just_expired():
            self.log.info("Disconnected, received no lookout message in "
                    "last_received_time")
            self.connected = False
            # Reset everything
            self.conn.reset()
            self.new_rx_id = Packet.UNKNOWN_ID


        if self.connected:
            self.lookout_timer.reset()
        elif self.lookout_timer.just_expired():
            self.log.info("Sending lookout message")
            self._send()
            self.lookout_timer.reset()

        if packet is None:
            pass
        elif packet.sender == self.conn.rx_id \
                and packet.receiver == self.conn.my_id:
            if packet.sequence_number >= self.conn.next_remote_seq:
                self.last_received_timer.reset()
                self.conn.next_remote_seq = packet.sequence_number + 1
                self.log.info("Got good packet")
                if packet.payload != self.score:
                    self.log.info("Packet received contains wrong score")
                    assert type(packet.payload) is bytes and \
                            len(packet.payload) == Packet.PAYLOAD_SIZE
                    if self.score != self.last_payload_sent or \
                            self.resend_same_countdown.just_expired():
                        self.log.info("Sending response data packet with new "
                                "score", Packet.payload_as_string(self.score))
                        self._send()
                        self.last_payload_sent = self.score
                        self.resend_same_countdown.reset()
                    else:
                        self.log.info("Not sending updated score as would be "
                        "duplicate within timeout")
            else:
                self.log.info("Got old/duplicate packet")

        elif packet.sender == self.new_rx_id \
                and packet.receiver == self.conn.my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            self.conn.reset(rx_id = self.new_rx_id)
            self.new_rx_id = Packet.UNKNOWN_ID
            self.new_connection_id_countdown.stop()
            self.log.info("Switching connection - new receiver:",
                    self.conn.rx_id, "and sending score")
            self._send()
            self.connected = True
            self.last_received_timer.reset()
            self.last_payload_sent = None

        else:
            if self.new_rx_id == Packet.UNKNOWN_ID:
                self.new_connection_id_countdown.reset()
                self.new_rx_id = gen_random(Packet.ID_SIZE,
                        excluding = (Packet.UNKNOWN_ID, self.conn.rx_id))
                self.log.info("Genning new rx_id", self.new_rx_id)
            self.log.info("Responding with id_change packet to :",
                    self.new_rx_id)
            self.conn.send_id_change_response(packet, self.new_rx_id,
                    self.receiver_ip_port)
            self.last_payload_sent = None

        return packet is not None

    def __del__(self):
        if self.sock is not None:
            self.sock.close()

#  async def sender_loop(log, args):
    #  # get_score_func must return bytes object of len Packet.PAYLOAD_SIZE that
    #  # will be sent across - ie. the score.

    #  log.info("\n\nSender started with params", args)

    #  log.debug("Initialising socket")

    #  with args.sock(log) as sock:

        #  log.debug("Initialising connection object")
        #  conn = BaseConnection(sock, log)

        #  new_rx_id = Packet.UNKNOWN_ID

        #  # When on and not connected, occasionally send out messages to the receiver
        #  # in case it's come up to alert it that we're switched on.
        #  lookout_timer = make_countdown_timer(
                #  seconds = args.lookout_timeout_seconds, started = True)

        #  # Timer from when receive message from new client. If don't get a response
        #  # within this timeout, will assume the client is switched off or we
        #  # received an old message.
        #  new_connection_id_countdown = make_countdown_timer(
                #  seconds = args.new_connection_id_countdown_seconds, started = False)

        #  # When connected, there can be periods of little to no network activity. The
        #  # receiver/client should ping this sender box with lookout messages to
        #  # confirm it's still there, ie. it hasn't been switched off. This is the
        #  # timeout for how long to wait until receiving one of those messages before
        #  # assuming the remote end is switched off and disconnecting. This should
        #  # therefore be realistically at least double the lookout_timeout in the
        #  # receiver.
        #  last_received_timer = make_countdown_timer(
                #  seconds = args.last_received_timer_seconds, started = False)
        #  connected = False

        #  # We use this to avoid resending the same score again in a short amount of
        #  # time.
        #  resend_same_countdown = make_countdown_timer(
                #  seconds = args.resend_same_countdown_seconds, started = True)

        #  # We use this to identify sending "same packet" again
        #  last_payload_sent = None

        #  #  score_reader = args.score_reader(log)
        #  score = (yield)
        #  if score is False:
            #  print("Quitting early from sending loop")
            #  return

        #  #  score = next(score_reader)
        #  log.info("Score:", Packet.payload_as_string(score))

        #  log.info("Sending out score")
        #  conn.sendto(score, args.receiver_ip_port)

        #  while True:

            #  # log.debug("--")

            #  # print("Packet size:", Packet.packet_size())
            #  packet, addr = conn.recvfrom(
                    #  timeout_ms = 0)
                    #  # timeout_ms = args.receive_loop_timeout_milliseconds)
            #  if addr != args.receiver_ip_port and addr is not None:
                #  log.warning("Received packet from", addr, "unexpected", args.receiver_ip_port)
            #  #  packet = Packet.from_bytes(sock.recv(Packet.packet_size(), timeout_ms = 3000))

            #  if packet is not None:
                #  log.info("Received:", packet)

            #  # Yield control back to main
            #  old_score = score
            #  score = (yield)
            #  if score is False:
                #  break
            #  #  score = next(score_reader)

            #  if new_connection_id_countdown.just_expired():
                #  log.info("New connection reply window expired, resetting new_rx_id")
                #  new_rx_id = Packet.UNKNOWN_ID
            #  if last_received_timer.just_expired():
                #  log.info("Disconnected, received no lookout message in last_received_time")
                #  connected = False
                #  # Reset everything
                #  conn.reset()
                #  new_rx_id = Packet.UNKNOWN_ID

            #  if connected:
                #  lookout_timer.reset()
            #  elif lookout_timer.just_expired():
                #  log.info("Sending lookout message")
                #  conn.sendto(score, args.receiver_ip_port)
                #  lookout_timer.reset()

            #  if packet is None:
                #  if old_score != score:
                    #  log.info("Score changed from", Packet.payload_as_string(old_score), "to",
                            #  Packet.payload_as_string(score), "- sending new score")
                    #  conn.sendto(score, args.receiver_ip_port)
                    #  last_payload_sent = score
                    #  lookout_timer.reset()

            #  elif packet.sender == conn.rx_id and packet.receiver == conn.my_id:
                #  if packet.sequence_number >= conn.next_remote_seq:
                    #  last_received_timer.reset()
                    #  conn.next_remote_seq = packet.sequence_number + 1
                    #  log.info("Got good packet")
                    #  if packet.payload != score:
                        #  log.info("Packet received contains wrong score")
                        #  assert type(packet.payload) is bytes and \
                                #  len(packet.payload) == Packet.PAYLOAD_SIZE
                        #  if score != last_payload_sent or \
                                #  resend_same_countdown.just_expired():
                            #  log.info("Sending response data packet with new score",
                                    #  Packet.payload_as_string(score))
                            #  conn.sendto(score, args.receiver_ip_port)
                            #  last_payload_sent = score
                            #  resend_same_countdown.reset()
                        #  else:
                            #  log.info("Not sending updated score as would be "
                            #  "duplicate within timeout")
                #  else:
                    #  log.info("Got old/duplicate packet")

            #  elif packet.sender == conn.rx_id and packet.receiver == Packet.UNKNOWN_ID:
                #  log.error("Got old discovery packet from current receiver - ignoring, "
                #  "this should never happen")
                #  #  assert False, "This should never happen anymore"

            #  elif packet.sender == new_rx_id and packet.receiver == conn.my_id \
                    #  and packet.id_change != Packet.UNKNOWN_ID:
                #  conn.reset(rx_id = new_rx_id)
                #  new_rx_id = Packet.UNKNOWN_ID
                #  new_connection_id_countdown.stop()
                #  log.info("Switching connection - new receiver:", conn.rx_id,
                        #  "and sending score")
                #  conn.sendto(score, args.receiver_ip_port)
                #  connected = True
                #  last_received_timer.reset()
                #  last_payload_sent = None

            #  else:
                #  if new_rx_id == Packet.UNKNOWN_ID:
                    #  new_connection_id_countdown.reset()
                    #  new_rx_id = gen_random(Packet.ID_SIZE,
                            #  excluding = (Packet.UNKNOWN_ID, conn.rx_id))
                    #  log.info("Genning new rx_id", new_rx_id)
                #  log.info("Responding with id_change packet to :", new_rx_id)
                #  conn.send_id_change_response(packet, new_rx_id,
                        #  args.receiver_ip_port)
                #  last_payload_sent = None

        #  print("Received close signal, stopping sending loop")

def receiver_loop(args):
    log = args.logger

    log.info("\n\nReceiver started with params", args)

    log.debug("Initialising socket")
    try:
        receiver_loop_impl(args)
    except Exception as e:
        args.sock.close()
        log.error("Exception raised:", str(e))
        raise

def receiver_loop_impl(args):
    sock, log = args.sock, args.logger

    log.debug("Initialising connection object")
    conn = BaseConnection(sock, log)

    lookout_timeout = make_countdown_timer(
            seconds = args.lookout_timeout_seconds, started = True)
    score = bytes(Packet.PAYLOAD_SIZE)
    client_addr = None

    log.debug("Initialising I2C writer")
    score_writer = args.score_writer(log)

    while True:
        #  log.debug("--")
        packet, addr = conn.recvfrom(
                timeout_ms = args.receive_loop_timeout_milliseconds)

        if packet is None:
            if lookout_timeout.just_expired():
                log.debug("Nothing received and lookout timeout expired, resetting it")
                lookout_timeout.reset()
                if client_addr is not None:
                    log.info("Sending lookout message to", client_addr)
                    conn.sendto(score, client_addr)
                else:
                    log.debug("Not sending lookout message as no client address")
        else:
            log.info("Received packet:", packet, "from", addr)
            if addr != client_addr:
                log.info("Packet is from new address:", addr,"- old address was:", client_addr)

        if packet is None:
            pass
        elif packet.sender == conn.rx_id and packet.receiver == conn.my_id \
                and packet.id_change == Packet.UNKNOWN_ID and client_addr == addr:
            if packet.sequence_number >= conn.next_remote_seq:
                conn.next_remote_seq = packet.sequence_number + 1
                log.info("Got good packet")
                if packet.payload != score:
                    score = packet.payload
                    # if probability(0.2, True, False):
                    #     print("Setting wrong score for testing")
                    #     # For testing, set wrong score
                    #     score = int_to_bytes(-1, 9)
                    log.info("Updating score to", Packet.payload_as_string(score),
                            "and echoing/sending back")
                    score_writer(score)
                    conn.sendto(score, addr)
                    client_addr = addr
                    #  lookout_timeout.reset()
                else:
                    log.debug("Taking no action as packet contains same score")
            else:
                log.info("Got old/duplicate packet")

        elif packet.receiver == conn.my_id and packet.id_change != Packet.UNKNOWN_ID:
            log.info("Changing id", conn.my_id, "->", packet.id_change,
                    "and sending id change, changing client addr to", addr)
            conn.change_and_send_connection_change(packet, addr)
            client_addr = addr

        else:
            log.info("Got unknown sending back my details")
            conn.sendto(score, addr)

#  import params

#  def main(argv):

    #  if len(argv) > 1:
        #  print("Receiver")
    #  else:
        #  # Problem atm is how to send stuff and receive and know stuff.
        #  print("Sender")
        #  with SimpleUDP(2521) as sock:
        #  #  with SimpleUDP(2521, "192.168.4.1", 2520) as sock:
            #  #  receiver_ip_port = "192.168.4.1", 2521
            #  sender_loop(sock, params.test_sender_args)

# if __name__ == "__main__":
#     sys.exit(main(sys.argv))

# # Sender
#         if packet is None:
#             if connected and old_score != score:

#         elif packet.sender == rx_id and packet.receiver == my_id \
#                 and packet.id_change == Packet.UNKNOWN_ID:
#             if packet.sequence_number >= next_remote_seq:
#                 if packet.payload != score:
#                     if score != last_payload_sent or \
#                             resend_same_countdown.just_expired():
#                     else:
#             else:

#         elif packet.sender == rx_id and packet.receiver == Packet.UNKNOWN_ID:

#         elif packet.sender == new_rx_id and packet.receiver == my_id \
#                 and packet.id_change != Packet.UNKNOWN_ID:

#         else:
#             if new_rx_id == Packet.UNKNOWN_ID:
# # Receiver

#         if packet is None: # Timed out or got garbled message
#             if lookout_timeout.just_expired():

#         elif packet.sender == rx_id and packet.receiver == my_id \
#                 and packet.id_change == Packet.UNKNOWN_ID:
#             if packet.sequence_number >= next_remote_seq:
#                 if packet.payload != score:
#             else:

#         elif packet.receiver == my_id and packet.id_change != Packet.UNKNOWN_ID:

#         else:
