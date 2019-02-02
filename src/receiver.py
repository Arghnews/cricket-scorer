import array
import machine
import time
import socket
import sys

from machine import Pin, I2C

from common import *

def init_listen_socket(port):
    print("Initialising tcp listening socket on port", port)
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(0)
    return sock

def i2c_write(i2c, addr, sub_byte, val):
    return
    try:
        i2c.writeto(addr, sub_byte)
        i2c.writeto(96, val)
        i2c.writeto(addr, b"\x00")
    except Exception as e:
        print("Exception during i2c_write with addr", addr, ", sub_byte",
                sub_byte, "val", val)
        raise

pin = Pin(2, Pin.OUT)
pin.value(1) # Active low, turn off

try:
    # Necessary for cleanup
    station = None
    listen_sock = None
    sock = None

    print("Initialising i2c")
    i2c = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)
    mux_channels = [(m, c)
            for m in array.array("B", [117, 118, 119])
            for c in [b"\x04", b"\x05", b"\x06"]]

    print("Connecting to network", SSID)
    station = station_init(RECEIVER_IP)
    while not station.isconnected():
        connect_to_network(station, SSID, WIFI_PASS)
        if not station.isconnected():
            time.sleep(5)
            flash_n_times(pin, 5)

    listen_sock = init_listen_socket(RECEIVER_PORT)
    listen_sock.settimeout(40)

    while True:
        print("Waiting for connections on", listen_sock)
        sock, addr = listen_sock.accept()
        sock.settimeout(7)
        print("Received connection from", addr)

        while True:
            # msg of type bytes
            print("Blocking read of size", MESSAGE_LEN, "bytes on socket...")
            msg = sock.read(MESSAGE_LEN)
            print("Read data of size", len(msg), "bytes:", list(msg))
            if len(msg) == 0:
                print("Connection closed by remote host - read 0 bytes - closing this socket")
                shutdown_socket(sock)
                break
            elif len(msg) != MESSAGE_LEN:
                # Could happen for short read?
                print("Discarding received data of wrong length")
            else:
                print("Setting i2c outputs according to received data")
                for (b, (mux, chan)) in zip(bytearray(msg), mux_channels):
                    i2c_write(i2c, mux, chan, bytes([0x44, b]))
                sock.write(b"\x00")

except Exception as e:
    sys.print_exception(e)
finally:
    print("Cleaning up")

    shutdown_socket(sock)
    del sock
    shutdown_socket(listen_sock)
    del listen_sock
    shutdown_station(station)
    del station
    gc.collect()

    print("Restarting")
    flash_n_times(pin, 4, gap_ms = 230)
    machine.reset()

