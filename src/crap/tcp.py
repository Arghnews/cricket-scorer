
def shutdown_socket(s):
    if s is None:
        return
    s.close()
    time.sleep_ms(100)

# Receiver
def init_listen_socket(port):
    print("Initialising tcp listening socket on port", port)
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(0)
    return sock

# Sender
# Setup tcp connection. Returns None if failed else returns socket
def tcp_connect(ip, port, socket_timeout):
    receiver_addr = socket.getaddrinfo(ip, port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(socket_timeout)
    t1 = time.ticks_ms()
    try:
        sock.connect(receiver_addr)
        return sock, None
    except OSError as e:
        print("Socket failed to connect to", receiver_addr, "-", e)
        sock.close()
        while time.ticks_diff(time.ticks_ms(), t1) < 5000:
            time.sleep(1)
        return None, e

# Sender
# Tries to setup tcp connection, throws if fails over tries times
def try_tcp_connect(ip, port, *, retries = 4, socket_timeout = 5):
    print("Making tcp socket connection to", ip, "-", port)
    for _ in range(retries + 1):
        sock, e = tcp_connect(RECEIVER_IP, RECEIVER_PORT, socket_timeout)
        if sock is not None:
            return sock
    raise e

