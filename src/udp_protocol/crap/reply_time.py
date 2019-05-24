#!/usr/bin/env python3

import operator
import socket
import sys
import threading
import time

from multiprocessing.pool import ThreadPool
from multiprocessing import cpu_count

PAYLOAD = bytes(range(5))
TCP_PORT = 5005

def echo_server(port):
    # https://wiki.python.org/moin/TcpCommunication
    TCP_IP = '127.0.0.1'
    BUFFER_SIZE = len(PAYLOAD)  # Normally 1024, but we want fast response

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((TCP_IP, port))
    s.listen(1)

    conn, addr = s.accept()
    # print("Connection address:", addr)
    if 1:
        data = conn.recv(BUFFER_SIZE)
        # if not data: break
        # print("Received data:", data)
        assert data == PAYLOAD
        conn.send(data)  # echo
    conn.close()

def echo_client(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect(("127.0.0.1", port))
    t1 = time.monotonic()
    s.send(PAYLOAD)
    data = s.recv(len(PAYLOAD))
    assert data == PAYLOAD
    t2 = time.monotonic()
    # print((t2 - t), "ms," ((t2 - t) / 1000), "s")
    s.close()
    return port, t2 - t1

def main(argv):

    ports = range(2519, 2523)
    server_threads = []
    for port in ports:
        thread = threading.Thread(target = echo_server, args = (port,))
        thread.start()
        server_threads.append(thread)

    time.sleep(1)

    with ThreadPool(processes = cpu_count()) as pool:
        for port, millis_taken in sorted(
                pool.map(echo_client, ports), key = operator.itemgetter(0)):
            print("Port: {}, {:.4f}s {:.4f}ms".format(
                port, millis_taken, millis_taken * 1000))

    for thread in server_threads:
        thread.join()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
