from dataclasses import dataclass

from cricket_scorer.net.packet import Packet


@dataclass
class ScoreData:
    """Holds the score in bytes and a string error message which may be empty"""
    score: bytes = bytes(Packet.PAYLOAD_SIZE)
    error_msg: str = ""

    def score_as_str(self):
        return Packet.payload_as_string(self.score)

    def __str__(self) -> str:
        # Must have brackets here, otherwise precedence of operators means
        # this doesn't behave how it is intended
        return Packet.payload_as_string(self.score) \
            + (", error: " + self.error_msg if self.error_msg else "")


# class ScoreData:
#     def __init__(self, score: bytes = bytes(Packet.PAYLOAD_SIZE), error_msg: str = ""):
#         self.score = score
#         self.error_msg = error_msg

#     def score_as_str(self):
#         return Packet.payload_as_string(self.score)

#     def __str__(self) -> str:
#         # Must have brackets here, otherwise precedence of operators means
#         # this doesn't behave how it is intended
#         return Packet.payload_as_string(self.score) \
#             + (", error: " + self.error_msg if self.error_msg else "")

#     def __eq__(self, o: object) -> bool:
#         if o is None:
#             return False
#         elif isinstance(o, ScoreData):
#             return self.score == o.score and self.error_msg == o.error_msg
#         raise NotImplementedError(
#             f"Comparison between objects of type ScoreData and {type(o)} not supported")
