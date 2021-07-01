import select
import socket

import cricket_scorer.misc.my_platform as my_platform


def _bytes_to_hex_string(b: bytes):
    assert isinstance(b, bytes)
    return f"bytes ({len(b)}) 0x: [" + \
        " ".join(["{:02x}".format(x) for x in b]) + "]"


class SimpleUDP:
    """Class owning and wrapping a UDP "listening" socket
    Supports context manager

    NOTE: This class reports short reads and write as failed receives/sends
    respectively since we expect a low error rate and this is simple.
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if any(exc_type, exc_value, traceback):
            self._log.debug(f"Error closing SimpleUDP {exc_type} {exc_value} " f"{traceback}")
        self.close()

    def close(self):
        self._log.debug(f"Closing socket id:{id(self)} {self._sock}")
        self._sock.close()

    def __init__(self, log, server_port, host_ip_bind="0.0.0.0"):
        self._log = log
        self._log.debug(f"SimpleUDP socket constructing id:{id(self)}, " f"on port:{server_port}")
        assert isinstance(server_port, int)
        server_addr = socket.getaddrinfo(host_ip_bind, server_port)[0][-1]
        #  client_addr = socket.getaddrinfo(client_ip, client_port)[0][-1]
        # UDP
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # https://stackoverflow.com/a/14388707
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(server_addr)
        self._sock.setblocking(False)

    def recvfrom(self, num_bytes, *, timeout_ms=50):
        """If data available to read, returns (data, addr)
        Else returns (None, None) after the timeout expires
        """
        assert num_bytes > 0, timeout_ms >= 0
        r, _, _ = select.select([self._sock], [], [], timeout_ms / 1000)
        if self._sock in r:
            try:
                data, addr = self._sock.recvfrom(num_bytes)
                self._log.debug(f"Recvd: {_bytes_to_hex_string(data)} from {addr}")
                if len(data) != num_bytes:
                    self._log.warning(
                        "Discarding message as received incorrect "
                        "number of bytes, expected", num_bytes, "but got", len(data), ":", data,
                        addr)
                if len(data) == num_bytes:
                    return data, addr
            except OSError as e:
                err_string = str(e)
                if my_platform.IS_WINDOWS and e.errno == 10054:
                    err_string += " - (very) likely can ignore IF testing on localhost"
                self._log.warning("udp_receive recv error:", err_string)
        return None, None

    def sendto(self, data, addr):
        assert type(data) is bytes
        _, w, _ = select.select([], [self._sock], [], 0)
        if self._sock in w:
            try:
                self._log.debug(f"Sending {_bytes_to_hex_string(data)} to {addr}")
                sent = self._sock.sendto(data, addr)
                if sent == len(data):
                    return True
            except OSError as e:
                self._log.warning(f"udp_receive.send error, sending to addr: {addr}: {e}")
        return False
