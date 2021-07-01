import time

from smbus2 import SMBus

from . import utils
from cricket_scorer.net.packet import Packet


class ScoreWriterI2cSingleDigit:
    def __init__(self, log):
        self._log = log

        self._log.debug("Initialising I2C bus object")
        self._bus = SMBus(1)
        self._addr = 0x27  # Wickets
        self._addr_index = 3

        values = list(range(9, -1, -1)) + [None]
        for v in values:
            utils.write_byte_safe(self._bus, self._log, self._addr, utils.INT_TO_DISPLAY[v])
            time.sleep(0.75)

    def __call__(self, score):
        assert self._addr_index >= 0 and self._addr_index < len(score)

        score = utils.sanitise_received_score(self._log, score, Packet.PAYLOAD_SIZE, False)

        if score is None:
            return

        digit = score[self._addr_index]

        self._log.debug("Writing new score digit", digit)
        utils.write_byte_safe(self._bus, self._log, self._addr, utils.INT_TO_DISPLAY[digit])
