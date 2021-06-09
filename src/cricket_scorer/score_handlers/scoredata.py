from recordclass import make_dataclass

from cricket_scorer.net.packet import Packet

ScoreData = make_dataclass("ScoreData", [("score", bytes), ("error_msg", str)],
        defaults=(bytes(Packet.PAYLOAD_SIZE), ""))

