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


class _BaseConnection:
    """Class that holds (but not owns) the socket and wraps things like the
    sequence numbers

    Variables aren't prefixed with underscores as they're accessed by the
    functions in this file, although currently the only one mutated not by a
    method is next_remote_seq. Struct like.
    """
    def __init__(self,
                 sock,
                 log,
                 my_id=None,
                 rx_id=Packet.UNKNOWN_ID,
                 next_remote_seq=SequenceNumber(bytes_=Packet.SEQUENCE_NUMBER_SIZE),
                 next_local_seq=SequenceNumber(bytes_=Packet.SEQUENCE_NUMBER_SIZE)):
        if my_id is None:
            my_id = gen_random(Packet.ID_SIZE, excluding=Packet.UNKNOWN_ID)

        self.sock: SimpleUDP = sock
        self.my_id = my_id
        self.rx_id = rx_id
        self.next_remote_seq = next_remote_seq
        self.next_local_seq = next_local_seq
        self.log = log

    def recvfrom(self, timeout_ms):
        data, addr = self.sock.recvfrom(Packet.packet_size(), timeout_ms=timeout_ms)
        if data is not None and len(data) != Packet.packet_size():
            self.log.error(f"Received wrong packet size, "
                           "logging and discarding. Packet: {data}")
            return None, None
        return Packet.from_bytes(data), addr

    def sendto(self, payload, addr):
        # print("Sending response data packet", packet)
        packet = Packet(sender=self.my_id,
                        receiver=self.rx_id,
                        sequence_number=self.next_local_seq.post_increment(),
                        payload=payload)
        self.log.debug("Sending packet:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    # Sender only
    def send_id_change_response(self, id_change_packet, new_rx_id, addr):
        packet = Packet(sender=self.my_id,
                        receiver=id_change_packet.sender,
                        id_change=new_rx_id,
                        payload=int_to_bytes(-1, Packet.PAYLOAD_SIZE))
        self.log.debug("Sending:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    # Receiver only
    def change_and_send_connection_change(self, id_change_packet, addr):
        old_my_id = self.my_id
        self.reset(my_id=id_change_packet.id_change, rx_id=id_change_packet.sender)
        packet = Packet(sender=id_change_packet.id_change,
                        receiver=id_change_packet.sender,
                        id_change=old_my_id,
                        payload=int_to_bytes(-1, Packet.PAYLOAD_SIZE))
        self.log.debug("Sending:", packet, "to", addr)
        return self.sock.sendto(packet.__bytes__(), addr)

    def reset(self, *, my_id=None, rx_id=Packet.UNKNOWN_ID):
        if my_id is not None:
            self.my_id = my_id
        self.rx_id = rx_id
        self.next_remote_seq = SequenceNumber(bytes_=Packet.SEQUENCE_NUMBER_SIZE)
        self.next_local_seq = SequenceNumber(bytes_=Packet.SEQUENCE_NUMBER_SIZE)


class Sender:
    def __init__(self, args):
        self._log = args.logger

        self._log.debug(f"Sender started with params:\n{args}")

        self._sock: SimpleUDP = args.sock

        self._log.debug("Initialising connection object")
        self._conn = _BaseConnection(self._sock, self._log)

        self._new_rx_id = Packet.UNKNOWN_ID

        self._lookout_timer = make_countdown_timer(seconds=args.lookout_timeout_seconds,
                                                   started=True)

        self._new_connection_id_countdown = make_countdown_timer(
            seconds=args.new_connection_id_countdown_seconds, started=False)

        self._last_received_timer = make_countdown_timer(seconds=args.last_received_timer_seconds,
                                                         started=False)
        self._connected = False

        self._resend_same_countdown = make_countdown_timer(
            seconds=args.resend_same_countdown_seconds, started=True)

        self._last_payload_sent = None

        self._score = None

        self._receiver_ip_port = args.receiver_ip_port

    def is_connected(self):
        return self._connected

    def _send(self):
        assert self._score is not None, "Must poll before sending score"
        self._log.debug("Sending score:", Packet.payload_as_string(self._score))
        self._conn.sendto(self._score, self._receiver_ip_port)
        self._last_payload_sent = self._score

    def poll(self, score: bytes):
        """Process incoming packets, update the connection with the latest score

        Update the connection with the latest score, process/respond to all
        queued incoming packets as required, send new score out if connected,
        send lookout messages if timeout has expired if not.
        """
        if self._score != score:
            old_score = self._score
            self._score = score

            self._log.debug(
                "Score changed from",
                Packet.payload_as_string(old_score) if old_score is not None else "no prior score",
                "to", Packet.payload_as_string(self._score), "- sending new score")
            self._send()
            self._last_payload_sent = self._score
            self._lookout_timer.reset()

        # Add timeout in case, highly unlikely it would ever be needed, but
        # don't want to get stuck looping here forever and the gui to block
        timeout = make_countdown_timer(millis=300, started=True)
        while self._poll() and not timeout.just_expired():
            pass

    def _poll(self):
        packet, addr = self._conn.recvfrom(timeout_ms=5)
        if addr is not None and addr != self._receiver_ip_port:
            self._log.warning("Received packet from", addr, "- expected", self._receiver_ip_port)

        if packet is not None:
            self._log.debug("Received:", packet, "from", addr)

        # Read score would have been here

        if self._new_connection_id_countdown.just_expired():
            self._log.debug("New connection reply window expired, resetting new_rx_id")
            self._new_rx_id = Packet.UNKNOWN_ID
        if self._last_received_timer.just_expired():
            self._log.debug("Disconnected, received no lookout message in last_received_time")
            self._connected = False
            # Reset everything
            self._conn.reset()
            self._new_rx_id = Packet.UNKNOWN_ID

        if self._connected:
            self._lookout_timer.reset()
        elif self._lookout_timer.just_expired():
            self._log.debug("Sending lookout message")
            self._send()
            self._lookout_timer.reset()

        if packet is None:
            pass
        elif packet.sender == self._conn.rx_id \
                and packet.receiver == self._conn.my_id:
            if packet.sequence_number >= self._conn.next_remote_seq:
                self._last_received_timer.reset()
                self._conn.next_remote_seq = packet.sequence_number + 1
                self._log.debug("Got good packet")
                if packet.payload != self._score:
                    self._log.debug("Packet received contains wrong score")
                    assert type(packet.payload) is bytes and \
                            len(packet.payload) == Packet.PAYLOAD_SIZE
                    if self._score != self._last_payload_sent or \
                            self._resend_same_countdown.just_expired():
                        self._log.debug("Sending response data packet with new "
                                        "score", Packet.payload_as_string(self._score))
                        self._send()
                        self._last_payload_sent = self._score
                        self._resend_same_countdown.reset()
                    else:
                        self._log.debug("Not sending updated score as would be "
                                        "duplicate within timeout")
            else:
                self._log.debug("Got old/duplicate packet")

        elif packet.sender == self._new_rx_id \
                and packet.receiver == self._conn.my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            self._conn.reset(rx_id=self._new_rx_id)
            self._new_rx_id = Packet.UNKNOWN_ID
            self._new_connection_id_countdown.stop()
            self._log.debug("Switching connection - new receiver:", self._conn.rx_id,
                            "and sending score")
            self._send()
            self._connected = True
            self._last_received_timer.reset()
            self._last_payload_sent = None

        else:
            if self._new_rx_id == Packet.UNKNOWN_ID:
                self._new_connection_id_countdown.reset()
                self._new_rx_id = gen_random(Packet.ID_SIZE,
                                             excluding=(Packet.UNKNOWN_ID, self._conn.rx_id))
                self._log.debug("Genning new rx_id", self._new_rx_id)
            self._log.debug("Responding with id_change packet to :", self._new_rx_id)
            self._conn.send_id_change_response(packet, self._new_rx_id, self._receiver_ip_port)
            self._last_payload_sent = None

        return packet is not None


def receiver_loop(args):
    log = args.logger

    log.info("Receiver started with params", args)

    try:
        receiver_loop_impl(args)
    except Exception as e:
        log.error("Exception raised:", str(e))
        raise


def receiver_loop_impl(args):
    sock, log = args.sock, args.logger

    log.debug("Initialising connection object")
    conn = _BaseConnection(sock, log)

    lookout_timeout = make_countdown_timer(seconds=args.lookout_timeout_seconds, started=True)
    score = bytes(Packet.PAYLOAD_SIZE)
    client_addr = None

    log.debug("Initialising I2C writer")

    while True:
        #  log.debug("--")
        packet, addr = conn.recvfrom(timeout_ms=args.receive_loop_timeout_milliseconds)

        if packet is None:
            if lookout_timeout.just_expired():
                log.debug("Nothing received and lookout timeout expired, " "resetting it")
                lookout_timeout.reset()
                if client_addr is not None:
                    log.info("Sending lookout message to", client_addr)
                    conn.sendto(score, client_addr)
                else:
                    log.debug("Not sending lookout message as no client " "address")
        else:
            log.info("Received packet:", packet, "from", addr)
            if addr != client_addr:
                log.info("Packet is from new address:", addr, "- old address was:", client_addr)

        if packet is None:
            pass
        elif packet.sender == conn.rx_id \
                and packet.receiver == conn.my_id \
                and packet.id_change == Packet.UNKNOWN_ID \
                and client_addr == addr:
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
                    args.score_writer(score)
                    conn.sendto(score, addr)
                    client_addr = addr
                    #  lookout_timeout.reset()
                else:
                    log.debug("Taking no action as packet contains same score")
            else:
                log.info("Got old/duplicate packet")

        elif packet.receiver == conn.my_id \
                and packet.id_change != Packet.UNKNOWN_ID:
            log.info("Changing id", conn.my_id, "->", packet.id_change,
                     "and sending id change, changing client addr to", addr)
            conn.change_and_send_connection_change(packet, addr)
            client_addr = addr

        else:
            log.info("Got unknown sending back my details")
            conn.sendto(score, addr)
