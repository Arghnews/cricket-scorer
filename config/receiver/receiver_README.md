todo: add instructions onto github bashrc thing for what to do
Have made empty executable node in /usr/bin/node to shut up nvim coc warnings

As per https://www.raspberrypi.org/documentation/configuration/wireless/access-point-routed.md
sudo rfkill unblock wlan
To enable wifi but added into /boot/cmdline.txt instead something else

To stop wpa_supplicant added 
interface wlx0013eff10ad3
	nohook wpa_supplicant
to /etc/dhcpcd.conf

Had to unmask hostapd
sudo systemctl unmask hostapd.service
Then enable and start it as for some reason was masked after following all the stuff from the webpage
Now it's up and running and the AP is too!

Wifi credentials in /etc/wpa_supplicant/wpa_supplicant-wlan0.conf  /etc/wpa_supplicant/wpa_supplicant-wlx1cbfce12740a.conf for each interface

In /etc/dhcpcd.conf
interface wlx1cbfce12740a
    static ip_address=192.168.4.2/24

Now it's managed by wpa_supplicant and connects to the right address

