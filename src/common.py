import time

SSID = "ESP8266_CRICKET"
WIFI_PASS = "ESP8266_CRICKET_PASS"
GATEWAY_IP = "192.168.1.1"

SENDER_IP = "192.168.1.100"
SENDER_PORT = 2520
RECEIVER_IP = "192.168.1.200"
RECEIVER_PORT = 2520

# SSID = "" # Home network SSID here
# WIFI_PASS = "" # Home network password here
# GATEWAY_IP = "192.168.1.1"

# SENDER_IP = "192.168.1.198"
# SENDER_PORT = 2520
# RECEIVER_IP = "192.168.1.199"
# RECEIVER_PORT = 2520


SENDER_MULTIPLEXERS = [113, 114, 115]
SENDER_CHANNELS = [4, 5, 6]

RECEIVER_MULTIPLEXERS = [117, 118, 119]
RECEIVER_CHANNELS = [4, 5, 6]

def flash_n_times(pin, n, *, gap_ms = 480):
    # Assumes active low
    for _ in range(n):
        pin.value(False)
        time.sleep_ms(20)
        pin.value(True)
        time.sleep_ms(gap_ms)
    pin.value(True)

