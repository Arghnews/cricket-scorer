# cricket_scorer overview

This project is to connect a mains powered digital (LEDs) cricket scoreboard over wifi to a laptop or remote control box, so that the latter can update the score on the scoreboard during a game of cricket. The "sender" (control box or laptop) runs a python program and sends data via UDP.

<br>

# To get the program
- These instructions are for Windows
- The app currently supports screen resolutions of 1366 by 768 and bigger
- Click [this link to go to the downloads page](https://github.com/Arghnews/cricket_scorer/releases/latest)

- Click to download the file that fits your Windows version and architecture:
  * For Windows 10 64bit or Windows 8 64bit use: cricket_scorer.Windows10.64bit.exe
- Double click and run the downloaded program
  - If you get Windows Smartscreen annoying stuff, click more options and run anyway
  - If you get a popup saying this app is by an unknown publisher, also click run
  - These features are complaining that this app isn't digitially signed using a certificate that has been verified by a certificate authority that Microsoft trusts. This requires a company, and may cost in the region of several hundred pounds per year, to check that your app isn't something nasty. Obviously this is not viable for a piece of free and open source software like this. Thus, please ignore this rubbish and click more options or run anyway etc. on the popups

- If you get Windows popups asking to allow the app through the firewall, please allow it
  * The app needs to receive data using UDP on port 2520 (and send data using UDP)

<br>

# Packages/programs used

License information for programs/packages used can be found in this repository **[here](src/cricket_scorer/data/licenses)**

- Python 3.7+ (compiled from source on raspberry pi raspbian)
- <div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>
- [PySimpleGUI](https://pysimplegui.readthedocs.io/en/latest/) for an easy to learn and use, fast to develop cross-platform GUI
- [plyer](https://pypi.org/project/plyer/) - desktop notifications
- [PyInstaller](https://www.pyinstaller.org/) - making one click executables
- [smbus2](https://pypi.org/project/smbus2/) - a nice i2c wrapper
- [xlwings](https://www.xlwings.org/) - reading from an Excel spreadsheet from python

<br>

# The architecture
```


________________________          UDP packets         _____________________________________
|     Control box      |    .                    .    |     Mark 1 Cricket Scoreboard     |
|                      |   //                    \\   |                                   |
|   Raspberry pi - i2c |__//                      \\__|     Raspberry pi - i2c bus        |
|    usb wifi antennae |--/                        \--|        Wifi access point          |
|______________________|                              |                                   |
                                                      |                                   |
                                                      |___________________________________|
       or

_________________________                       .     _____________________________________
|     PC or Laptop     |    .                   \\    |     Mark 2 Cricket Scoreboard     |
|                      |   //                    \\   |                                   |
|                      |__//                      \\__|   Raspberry pi - i2c bus          |
|        wifi antennae |--/                        \--|       Wifi access point           |
|                      |                              |                                   |
|   Microsoft Excel    |                              |                                   |
|         ⇅            |                             |                                    |
|GUI cricket_scorer app|                              |                                   |
|______________________|                              |___________________________________|

```

### Control box:
A wooden box with a raspberry pi inside connected to a power source like big phone charging power brick via (micro) usb or usb-c. It runs headless raspbian and a python program. On startup it attempts to connect to a wifi network created by either of the scoreboards. The python program reads via the i2c bus the status of several shift registers that are connected to microswitches which are labelled with digits 0-9. 9 digits: 3 for the total, 3 for the 1st innnings, 1 for the wickets, 2 for the overs. The python program sends the score to the receiver over the wifi network. The receiver always has the same IP and uses the same port. It will continue to send the score on any changes, or when an incorrect/out of date score is echoed back by the receiver.

### The Mark 1 Cricket Scoreboard
Originally this consisted of two esp8266 boards. Each of these was running micropython. One of these created a wifi network and acted only as a router/access point. The other wirelessly connected to this network. Similar to the control box, in order to get round a lack of addresses, it used multiplexers and connected to these via the i2c bus this time to write and set the state of LEDs on the board to display the score. It listened over the network for connections from the sender for the score. For ease of setup, TCP was used.

In the latest iteration, the mark 1 now is just a raspberry pi running normal python (hooray!). It still uses the i2c bus and multiplexers to write the score, running a python program with a UDP protocol designed to avoid wasting sending old data that TCP would have to. This raspberry pi also acts as the access point for its own wifi network that a sender may connect to.

This is powered by a mains connection, and the required electronic circuitry inside to power the raspberry pi via the appropriate GPIO pin.

### The Mark 2 Cricket Scoreboard
Similar to the Mark 1. A raspberry pi inside running python, connected via i2c. This raspberry pi is connected via i2c to several PCF8574(n) expander chips through which it is able to write data to light up the LEDs on the scoreboard. This scoreboard splits off into several physical parts, as otherwise it's quite heavy. The wires that the i2c connections run over are quite long for some of the boards, leading to occassional connection issues. Whilst both the control box and the Mark 1 scoreboard use whip antennaes, this one has a bigger long range usb wifi antennae connected. It has been tested to receive signal across roughly a 200metre unobstructed field. Also mains connected for power.

### PC or Laptop
Runs the GUI cricket_scorer app python app. When run, the app uses xlwings to read the score from 4 cells a Microsoft Excel spreadsheet - total, overs, wickets, 1st innings. The computer must be connected to the CRICKET0 wifi network created by a receiving scoreboard. It will then send the score data via UDP over wifi to the scoreboard to set the score.

<br>

# License

This software is licensed under GNU Lesser General Public License v3.0

See LICENSE.txt and COPYING.LESSER for more information. Done this way as per [choosealicense](https://choosealicense.com/licenses/lgpl-3.0/)
