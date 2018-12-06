import network
import time

SSID = "ESP8266_CRICKET"
WIFI_PASS = "ESP8266_CRICKET_PASS"
GATEWAY_IP = "192.168.1.1"
SENDER_IP = "192.168.1.100"
RECEIVER_IP = "192.168.1.200"
RECEIVER_PORT = 2520
MESSAGE_LEN = 9 # Bytes

def station_init(ip, gateway = GATEWAY_IP):
    station = network.WLAN(network.STA_IF)
    # Must be active for config on at least some esp8266 versions
    station.active(True)
    station.ifconfig((ip, "255.255.255.0", gateway, "8.8.8.8"))
    return station

# Connect, 5 second timeout
def connect_to_network(station, ssid, password, pin, timeout = 5):
    station.connect(ssid, password)
    for _ in range(timeout):
        if station.isconnected():
            return True
        time.sleep(1)
    return False

def flash_n_times(pin, n):
    # Assumes active low
    for _ in range(n):
        pin.value(False)
        time.sleep_ms(20)
        pin.value(True)
        time.sleep_ms(580)
    pin.value(True)

