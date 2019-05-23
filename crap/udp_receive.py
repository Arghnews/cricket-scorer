#!/usr/bin/env python3

import operator
import sys
import select
import socket
import time

from countdown_timer import make_countdown_timer

class SimpleUDP:
    """
    NOTE: This class reports short reads and write as failed receives/sends
    respectively since we expect a low error rate and this is simple.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Closing socket")
        # self.poller.unregister(self.sock)
        self.sock.close()

    def __init__(self, server_port, client_ip, client_port):
        server_addr = socket.getaddrinfo("0.0.0.0", server_port)[0][-1]
        client_addr = socket.getaddrinfo(client_ip, client_port)[0][-1]
        # UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # https://stackoverflow.com/a/14388707
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind(server_addr)
        self.sock.connect(client_addr)
        # self.poller = select.poll()
        # self.poller.register(self.sock)

        # https://docs.micropython.org/en/latest/library/usocket.html#usocket.socket.sendall
        # socket.sendall on non-blocking sockets is undefined behaviour on
        # micropython, use write instead
        if sys.implementation.name == "micropython":
            self.send_func = self.sock.write
        else:
            self.send_func = self.sock.sendall

    # Despite https://docs.micropython.org/en/latest/library/usocket.html#usocket.socket.settimeout
    # recommending use of (u)select.poll on micropython ports, it does not seem
    # to work. If you send/recv and the first fails, all further polls using
    # select.poll on the socket will fail.
    # Solution: just try the recv and sends, don't poll first to check if "can"

    def recv(self, num_bytes, *, timeout_ms = 50):
        assert num_bytes > 0, timeout_ms >= 0
        n = min(10, timeout_ms)
        timeout = make_countdown_timer(millis = timeout_ms / n)
        for _ in range(n):
            timeout.reset()
            try:
                data = self.sock.recv(num_bytes)
                if len(data) == num_bytes:
                    return data
            except OSError:
                pass
            timeout.sleep_till_expired()
        return None

    def send(self, data):
        assert type(data) is bytes
        try:
            sent = self.send_func(data)
            if sent == len(data):
                return True
        except OSError:
            pass
        return None

    # def _check_socket(self, poll_type, timeout_ms):
    #     self.poller.modify(self.sock, poll_type)
    #     return any(event & poll_type
    #             for _, event in self.poller.poll(timeout_ms))

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
