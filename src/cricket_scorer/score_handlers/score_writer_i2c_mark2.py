import time
from functools import partial

from smbus2 import SMBus

from . import utils


# Preserves order
def remove_duplicates(l):
    ll, s = [], set()
    for x in l:
        if x not in s:
            ll.append(x)
        s.add(x)
    return ll


# Run on the scoreboard itself
class ScoreWriterI2cMark2:
    def __init__(self, log):
        self._log = log
        self._addrs = [
            #0x3c, 0x3d, 0x3f, # Total # Old total
            0x22,
            0x3d,
            0x3f,  # Total
            0x27,  # Wickets
            0x25,
            0x24,  # Overs
            0x39,
            0x3b,
            0x3e  # 1st innings
        ]

        self._pre_off_value = 0x08

        self._log.debug("Initialising I2C bus object")
        self._bus = SMBus(1)

        self._read_byte = partial(utils.read_byte_else, self._bus, self._log)
        self._write_byte = partial(utils.write_byte_safe, self._bus, self._log)

        # This should come last in the constructor
        self._startup_sequence()

    def _startup_sequence(self):
        self._log.debug("Performing startup sequence")
        values = list(range(9, -1, -1))
        #  values = list(range(1, -1, -1)) + [None]
        for v in values:
            time.sleep(1)
            #  time.sleep(0.1)
            val = bytes([v] * len(self._addrs))
            self._set_score(val, False)

    def _set_score(self, score, blank_out_leading_zeroes=True):
        score = utils.sanitise_received_score(self._log, score, len(self._addrs),
                                              blank_out_leading_zeroes)

        if score is None:
            return

        error_addresses = []

        self._log.debug("Setting score to", list(score))

        for addr, digit in zip(self._addrs, score):
            current_output = self._read_byte(addr, self._pre_off_value)

            s = ""
            if current_output in utils.display_to_int:
                s = str(utils.display_to_int[current_output])
            else:
                s = "unknown value (" + str(hex(current_output)) + ")"
            s += ","

            self._log.info("Addr:", hex(addr), "current digit:", s, "new digit:", digit)

            if current_output == utils.INT_TO_DISPLAY[digit]:
                # We are already displaying this digit, make no change
                continue

            time.sleep(0.1)
            success = True
            # Special treatment for displaying fully off digits
            if digit == None:
                time.sleep(0.05)
                success = self._write_byte(addr, self._pre_off_value)
                time.sleep(0.1)
            if not self._write_byte(addr, utils.INT_TO_DISPLAY[digit]) or \
                    not success:
                self._log.error("Adding addr", hex(addr), "digit", digit, "to error_addresses")
                error_addresses.append(addr)

        if error_addresses:
            self._log.debug("Error addresses:", list(hex(x) for x in error_addresses))

        for addr in error_addresses:
            expected_digit = score[self._addrs.index(addr)]
            raw_value = self._read_byte(addr, None)
            if raw_value is not None and raw_value in utils.display_to_int \
                    and utils.display_to_int[raw_value] == expected_digit:
                self._log.info("Error addr", addr, "seems to be reading the "
                               "expected value", expected_digit, "so ignoring it")
            else:
                self.flip(addr, score)

    def __call__(self, score):
        self._set_score(score)

    def flip(self, bad_addr, score):
        # This is another attempt to fix digits that won't turn off or are stuck
        # by setting adjacent digits first, then setting the bad one to the
        # value we want, then setting the adjacent digits back

        bad_index = self._addrs.index(bad_addr)
        # Get the addrs either side to flip
        adjacent_indexes = [g % len(self._addrs) for g in [bad_index - 1, bad_index + 1]]

        adjacent_addrs = [self._addrs[i] for i in adjacent_indexes]

        adjacent_addrs = remove_duplicates(adjacent_addrs)
        if bad_addr in adjacent_addrs:
            adjacent_addrs.remove(bad_addr)

        self._log.warning("Trying to fix", hex(bad_addr), "by flipping", hex(adjacent_addrs[0]),
                          "and", hex(adjacent_addrs[1]))

        self._log.info(bad_addr, adjacent_addrs)
        if len(adjacent_addrs) == 0:
            self._log.info("In flipping of", hex(bad_addr), "no adjacent addresses")

        for addr in adjacent_addrs:
            self._write_byte(addr, self._pre_off_value)
            time.sleep(0.1)

        time.sleep(0.2)
        self._write_byte(bad_addr, self._pre_off_value)
        time.sleep(0.5)
        self._write_byte(bad_addr, utils.INT_TO_DISPLAY[None])
        time.sleep(0.5)

        for addr in adjacent_addrs:
            self._write_byte(addr, utils.INT_TO_DISPLAY[score[self._addrs.index(addr)]])
            time.sleep(0.1)

        self._log.warning("Done with flip fix for", hex(bad_addr))

        # The comment block below about the 1st innings 1st digit fix
        # specifically is somewhat outdated.
        # The problem is strange and is not consistent. Sometimes the digits
        # behave nicely, sometimes they don't.

        # 1st innings 1st digit won't turn off fix
        # We have an output issue when setting digits to completely off ie. to
        # display the value "None", likely due to electrical noise on the I2C
        # bus.
        # This particularly happens on the "bad" address (variable below). We
        # apply a fix when this is detected of flipping the adjacent digit to
        # some value that is on, then turning off the bad digit again, then
        # flipping the adjacent digit back to what it should be. Seems to work
        # for now.
        # Luckily (I'm told) in a cricket game the 1st innings value is set to
        # 000 at the outset, then a value at halftime, and the problem sems to
        # mostly occur when setting the value 900, which would be absurdly rare
        # anyway, so this fix should more than suffice.
        #  bad = self.first_innings_problem_first_digit
        #  good = self.first_innings_adjacent_first_digit_fix

        #  print("Addrs:", [hex(addr) for addr in self.addrs])
        #  print("Score:", Packet.payload_as_string(score))
        #  co = [display_to_int[bus_read_byte_else(self.bus, self.log, addr, self.pre_off_value)]
        #  for addr in self.addrs]
        #  print("Current:", co)

        #  # This relies on 0x39 being followed by 0x3b in the addrs
        #  if addr == bad and bad in self.addrs and good in self.addrs \
        #  and self.addrs[self.addrs.index(bad) + 1] == good:
        #  self.log.warning("Problem child of 1st innings", hex(bad), "has errored, "
        #  "trying to fix by flipping the adjacent digit at", hex(good))
        #  self.bus.write_byte(good, pre_off_value)
        #  time.sleep(0.5)
        #  self.bus.write_byte(bad, pre_off_value)
        #  time.sleep(0.5)
        #  self.bus.write_byte(bad, int_to_display[None])
        #  time.sleep(0.5)
        #  self.bus.write_byte(good,
        #  int_to_display[score[self.addrs.index(good)]])

    # Returns an array of 9 bytes
    # 3 total, 1 wickets, 2 overs, 3 1st innings. Bytes breakdown.
    # Bytes are little endian integers, ie. 0x00 == 0, 0x01 == 1
