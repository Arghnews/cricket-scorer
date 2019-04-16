#!/usr/bin/env python3

import operator
import sys
import select
import socket
import time

class ConnectionClosedException(Exception):
    def __init__(self, message):
        super().__init__(message)

class SendFailedException(Exception):
    def __init__(self, message):
        super().__init__(message)

class SimpleUDP:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Closing socket")
        self.poller.unregister(self.sock)
        self.sock.close()

    def __init__(self, server_port, client_ip, client_port,
            *, backup_timeout = 30):
        server_addr = socket.getaddrinfo("0.0.0.0", server_port)[0][-1]
        client_addr = socket.getaddrinfo(client_ip, client_port)[0][-1]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind(server_addr)
        self.sock.connect(client_addr)
        self.poller = select.poll()
        self.poller.register(self.sock)

    def recv(self, numb_bytes, timeout_ms):
        if not self._check_socket(select.POLLIN, timeout_ms):
            return None
        # If here we got an event that is a POLLIN ie. there is data to be read
        data = self.sock.recv(numb_bytes)
        print("Data read", data)

        # Connection closed
        if len(data) == 0:
            raise RuntimeError("Connection closed by remote - read of 0 bytes")
        return data

    # Return value subject to change - returns number of bytes sent
    def send(self, data):
        if not self._check_socket(select.POLLOUT, 0):
            return None
        # If here we got an event that is a POLLIN ie. there is data to be read
        return self.sock.send(data)

    def _check_socket(self, poll_type, timeout_ms):
        self.poller.modify(self.sock, poll_type)
        events = self.poller.poll(timeout_ms)
        # We know that all fds will be this socket so can ignore them
        if not events:
            return False
        print("Events received", events)
        for fd, event in events:
            assert fd == self.sock.fileno()
            if event != select.POLLIN:
                raise OSError("Error - socket expected to be able to recv (" +
                        str(self.sock) + "):" + str(POLL_EVENTS[event]))
        return True

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

POLL_EVENT = {
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

def main(argv):

    receiver = False
    if len(argv) > 1:
        receiver = True

    # https://stackoverflow.com/questions/3069204/reading-partially-from-sockets
    # UDP recv dequeues whole datagram at a time
    # NOTE: in rare cases recv can still block even after the select poll

    if receiver:
        with SimpleUDP(2520, "127.0.0.1", 2521) as udp_sock:
            input("Waiting for input")
            while True:
                print(udp_sock.recv(2, 5000))
    else:
        with SimpleUDP(2521, "127.0.0.1", 2520) as udp_sock:
            while True:
                print("Sending", udp_sock.sock.send(bytes([1,2,3])))
                time.sleep(2)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
