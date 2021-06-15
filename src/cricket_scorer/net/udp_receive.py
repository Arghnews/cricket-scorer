#!/usr/bin/env python3

import sys
import select
import socket
import time

from .countdown_timer import make_countdown_timer
import cricket_scorer.misc.my_platform as my_platform

class SimpleUDP:
    """
    NOTE: This class reports short reads and write as failed receives/sends
    respectively since we expect a low error rate and this is simple.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # if any(exc_type, exc_value, traceback):
        print(exc_type, exc_value, traceback)
        self.close()

    def close(self):
        self.log.info("Closing socket")
        # self.poller.unregister(self.sock)
        self.sock.close()

    def __init__(self, log, server_port, host_ip_bind = "0.0.0.0"):
        assert isinstance(server_port, int)
        server_addr = socket.getaddrinfo(host_ip_bind, server_port)[0][-1]
        #  client_addr = socket.getaddrinfo(client_ip, client_port)[0][-1]
        # UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # https://stackoverflow.com/a/14388707
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Holy balls batman, what is this line... Windows no likey
        self.sock.bind(server_addr)
        self.sock.setblocking(False)
        self.log = log
        #  self.sock.connect(client_addr)
        # self.poller = select.poll()
        # self.poller.register(self.sock)

        # https://docs.micropython.org/en/latest/library/usocket.html#usocket.socket.sendall
        # socket.sendall on non-blocking sockets is undefined behaviour on
        # micropython, use write instead
        # Now using socket.sendto for both
        self.send_func = self.sock.sendto
        #  if sys.implementation.name == "micropython":
            #  self.send_func = self.sock.write
        #  else:
            #  self.send_func = self.sock.sendall

    def recvfrom(self, num_bytes, *, timeout_ms = 50):
        """If data available to read, returns (data, addr)
        Else returns (None, None) after the timeout expires
        """
        assert num_bytes > 0, timeout_ms >= 0
        # n = max(1, min(10, timeout_ms))
        # timeout = make_countdown_timer(millis = timeout_ms / n)
        r, _, _ = select.select([self.sock], [], [], timeout_ms / 1000)
        if self.sock in r:
            # print(r, x)
            try:
                data, addr = self.sock.recvfrom(num_bytes)
                # print("Recvd:", data, addr)
                if len(data) != num_bytes:
                    self.log.warning("Discarding message as received incorrect "
                    "number of bytes, expected", num_bytes, "but got", len(data),
                    ":", data, addr)
                if len(data) == num_bytes:
                    return data, addr
            except OSError as e:
                err_string = str(e)
                if my_platform.IS_WINDOWS and e.errno == 10054:
                    err_string += "- (very) likely can ignore IF testing on localhost"
                self.log.warning("udp_receive recv error:", err_string)
        # timeout.sleep_till_expired()
        return None, None

    def sendto(self, data, addr):
        assert type(data) is bytes
        _, w, x = select.select([], [self.sock], [], 0)
        if self.sock in w:
            try:
                sent = self.sock.sendto(data, addr)
                # print("Sent:", sent)
                if sent == len(data):
                    return True
            except OSError as e:
                self.log.warning("udp_receive.send error:", e)
                pass
        return False


# POLL_EVENTS = {
#         1: "POLLIN",
#         2: "POLLPRI",
#         4: "POLLOUT",
#         8: "POLLERR",
#         16: "POLLHUP",
#         32: "POLLNVAL",
#         64: "POLLRDNORM",
#         128: "POLLRDBAND",
#         256: "POLLWRNORM",
#         512: "POLLWRBAND",
#         1024: "POLLMSG",
#         8192: "POLLRDHUP",
# }

# def all_events(mask):
#     val = 2 ** 13
#     events = []
#     while mask > 0:
#         if val <= mask:
#             mask -= val
#             if val in POLL_EVENTS:
#                 events.append(POLL_EVENTS[val])
#         val //= 2
#     return ", ".join(events)
#     # POLL_EVENTS

# def gen():
#     import select
#     poll_codes = sorted(
#             [
#                 (a, getattr(select, a))
#                 for a in dir(select) if a.startswith("POLL")
#             ],
#             key = operator.itemgetter(1))
#     # print("\n".join(
#     #         str(val) + ": \"" + name + "\"," for name, val in poll_codes
#     #         ))
#     return dict(poll_codes)

def main(argv):
    # print(all_events(9))
    # return

    receiver = False
    if len(argv) > 1:
        receiver = True

    # https://stackoverflow.com/questions/3069204/reading-partially-from-sockets
    # UDP recv dequeues whole datagram at a time
    # NOTE: in rare cases recv can still block even after the select poll

    if receiver:
        with SimpleUDP(2520, "127.0.0.1", 2521) as udp_sock:
            # input("Waiting for input")
            while True:
                print(udp_sock.recv(10, 5000))
    else:
        with SimpleUDP(2521, "127.0.0.1", 2520) as udp_sock:
            while True:
                print("Sending", udp_sock.sock.send(bytes([1,2,3,5,6,7,8])))
                time.sleep(2)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
