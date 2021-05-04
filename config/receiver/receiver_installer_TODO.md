copy files over
raspi-config, unblock wifi, set wifi, set predictable ifnames, set I2C on, set no wait for network at boot, set console autologin, enable ssh
update
install vim, git, my bashrc clone, comment out the coc.nvim plugin
Follow "raspberry pi router" tutorial on official site
Copy over hostapd, dnsmasq, wpa_supplicant, dhcpcd config files
Install wireless adapter drivers
    - Mark 1: Install the morrownr/8821cu driver for the wireless adapter, long range WIP antenna
    - Mark 2: Super long range antenna, can't remember the driver, maybe it just worked,
    otherwise find the chipset again and follow the instructions
Set core frequencies to be fixed so as not to interfere with I2C bus in /boot/config.txt
Install python3-pip and then install smbus2 from pip
Move over files for udp protocol plus the wifi and startup scripts and service files, make links to them

This list may be incomplete as I've forgotten stuff

