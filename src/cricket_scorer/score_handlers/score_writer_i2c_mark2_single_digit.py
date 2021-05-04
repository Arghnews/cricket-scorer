import time

from smbus2 import SMBus

from . import utils
from cricket_scorer.net.packet import Packet

class ScoreWriterI2cSingleDigit:
    def __init__(self, log):
        self.log = log

        self.log.debug("Initialising I2C bus object")
        self.bus = SMBus(1)
        self.addr = 0x27 # Wickets
        self.addr_index = 3

        values = list(range(9, -1, -1)) + [None]
        for v in values:
            utils.write_byte_safe(self.bus, self.log, self.addr,
                    utils.int_to_display[v])
            time.sleep(0.75)

    def __call__(self, score):
        assert self.addr_index >= 0 and self.addr_index < len(score)

        score = utils.sanitise_received_score(self.log, score,
                Packet.PAYLOAD_SIZE, False)

        if score is None:
            return

        digit = score[self.addr_index]

        self.log.debug("Writing new score digit", digit)
        utils.write_byte_safe(self.bus, self.log, self.addr,
                utils.int_to_display[digit])

