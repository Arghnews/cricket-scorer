#!/usr/bin/env python3

import operator
import sys
import select
import socket
import time

class SimpleUDP:
    """
    NOTE: This class reports short reads and write as failed receives/sends
    respectively since we expect a low error rate and this is simple.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Closing socket")
        self.poller.unregister(self.sock)
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
        self.poller = select.poll()
        self.poller.register(self.sock)

    # TODO: remove/change/think about these quick and dirty try blocks

    # Have chosen to return None to try and help remove ambiguity in case a zero
    # length payload is sent/received and code goes: if connc.recv(n, t):...
    # Returns None on failure, bytes object on success
    def recv(self, num_bytes, *, timeout_ms = 50):
        try:
            if not self._check_socket(select.POLLIN, timeout_ms):
                print("Nothing to read from socket")
                return None
            # If here we got an event that is a POLLIN ie. there is data to be read
            # print(num_bytes)
            data = self.sock.recv(num_bytes)
            # print("Data read", data)
            if len(data) != num_bytes:
                print("Read", len(data), "bytes but was expecting", num_bytes)
                return None
            return data
        except Exception:
            pass

    # Returns None on failure, bytes object on success
    def send(self, data):
        try:
            print("self._check_socket(select.POLLOUT, 0):", self._check_socket(select.POLLOUT, 0))
            if not self._check_socket(select.POLLOUT, 50):
                return None
            # If here we got an event that is a POLLIN ie. there is data to be read
            sent = self.sock.send(data)
            print("Sent data in udp::send", list(map(int, data)), ", bytes sent:", sent)
            if len(data) != sent:
                return None
            return True
        except Exception:
            pass

    def _check_socket(self, poll_type, timeout_ms):
        return True
        self.poller.modify(self.sock, poll_type)
        events = self.poller.poll(timeout_ms)
        # We know that all fds will be this socket so can ignore them
        if not events:
            print("No poll events to read from socket")
            return False
        # print("Events received", events)
        for fd, event in events:
            print("fd, events:", fd, all_events(event))
            # print(self.sock.fileno())
            # assert fd == self.sock.fileno()
            # On Micropython these don't compare equal - suppose no notion of
            # file descriptors etc.
            if event != poll_type:
                raise OSError("Error - socket expected to be able to {} ({}): {}"
                        .format(
                        "recv" if poll_type == select.POLLIN else "send",
                        self.sock, all_events(event)))
        return True

POLL_EVENTS = {
        1: "POLLIN",
        2: "POLLPRI",
        4: "POLLOUT",
        8: "POLLERR",
        16: "POLLHUP",
        32: "POLLNVAL",
        64: "POLLRDNORM",
        128: "POLLRDBAND",
        256: "POLLWRNORM",
        512: "POLLWRBAND",
        1024: "POLLMSG",
        8192: "POLLRDHUP",
}

def all_events(mask):
    val = 2 ** 13
    events = []
    while mask > 0:
        if val <= mask:
            mask -= val
            if val in POLL_EVENTS:
                events.append(POLL_EVENTS[val])
        val //= 2
    return ", ".join(events)
    # POLL_EVENTS

def gen():
    import select
    poll_codes = sorted(
            [
                (a, getattr(select, a))
                for a in dir(select) if a.startswith("POLL")
            ],
            key = operator.itemgetter(1))
    # print("\n".join(
    #         str(val) + ": \"" + name + "\"," for name, val in poll_codes
    #         ))
    return dict(poll_codes)

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
