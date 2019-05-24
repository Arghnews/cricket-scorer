import machine
import sys
import time

import connection
import simple_i2c
import udp_receive
import wifi

from common import *

pin = machine.Pin(2, machine.Pin.OUT)
pin.value(1) # Active low, turn off

try:
    print("Initialising i2c")
    i2c = simple_i2c.SimpleI2C(
            multiplexers = RECEIVER_MULTIPLEXERS, channels = RECEIVER_CHANNELS,
            scl = machine.Pin(5), sda = machine.Pin(4), freq = 100000)

    print("Connecting to network", SSID)
    station = wifi.station_init(RECEIVER_IP)
    while not wifi.connect_to_network(station, SSID, WIFI_PASS):
        print("Attempting to connect to network", SSID)
        time.sleep(5)
        flash_n_times(pin, 5)
    get_score = lambda: i2c.read()

    print("Going into receive loop")
    with udp_receive.SimpleUDP(RECEIVER_PORT, SENDER_IP, SENDER_PORT) as sock:
        connection.receiver_loop(sock)

except Exception as e:
    sys.print_exception(e)
finally:
    print("Cleaning up")

    wifi.shutdown_station(station)
    gc.collect()

    print("Restarting")
    flash_n_times(pin, 8, gap_ms = 230)
    machine.reset()

