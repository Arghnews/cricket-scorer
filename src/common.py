import network
import time

SSID = "ESP8266_CRICKET"
WIFI_PASS = "ESP8266_CRICKET_PASS"
GATEWAY_IP = "192.168.1.1"
SENDER_IP = "192.168.1.100" # FIXME: HAVE CHANGED THIS CHANGE ME BACK
RECEIVER_IP = "192.168.1.200"
RECEIVER_PORT = 2520
MESSAGE_LEN = 9 # Bytes

def station_init(ip, gateway = GATEWAY_IP):
    station = network.WLAN(network.STA_IF)
    # Must be active for config on at least some esp8266 versions
    station.active(True)
    print("station init: " + str(station))
    station.ifconfig((ip, "255.255.255.0", gateway, "8.8.8.8"))
    print(station.ifconfig())
    return station

WLAN_STATUS_TO_STR = {
        network.STAT_IDLE: "STAT_IDLE",
        network.STAT_CONNECTING: "STAT_CONNECTING",
        network.STAT_WRONG_PASSWORD: "STAT_WRONG_PASSWORD",
        network.STAT_NO_AP_FOUND: "STAT_NO_AP_FOUND",
        network.STAT_CONNECT_FAIL: "STAT_CONNECT_FAIL",
        network.STAT_GOT_IP: "STAT_GOT_IP",
        }

def wlan_status_str(station):
    if station is None:
        return "station is NULL - no status"
    return WLAN_STATUS_TO_STR.get(station.status(), "UNKNOWN STATUS")

# Connect, 5 second timeout
def connect_to_network(ip, gateway, station, ssid, password, timeout = 5):

    print("In connect to network")
    print("Params :" + str(" ".join(map(str, [ip, gateway, station, ssid, password, timeout]))))

    if station is not None:
        print("Station not none deleting")
        print("Old station status: " + wlan_status_str(station))
        station.disconnect()
        station.active(False)
        del station

    time.sleep(1)
    print("Init station")
    station = station_init(ip, gateway)
    print(wlan_status_str(station))

    try:
        print(station.scan())
    except OSError as e:
        print("Scan resulted in " + str(e))

    print("Connecting to " + ssid + " " + password)
    station.connect(ssid, password)
    for _ in range(timeout):
        print("Station status " + wlan_status_str(station))
        if station.isconnected():
            return station, True
        print("Failed to connect sleeping")
        time.sleep(1)
    print("Failed to connect n times returning False")
    return station, False

def flash_n_times(pin, n):
    # Assumes active low
    for _ in range(n):
        pin.value(False)
        time.sleep_ms(20)
        pin.value(True)
        time.sleep_ms(580)
    pin.value(True)

