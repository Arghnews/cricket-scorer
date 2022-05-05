import xml.etree.ElementTree as ET

import dataclasses
import itertools
import typing

from cricket_scorer.score_handlers.scoredata import ScoreData
# from . import utils


def get_score_reader(logger):
    return ScoreReaderXml(logger)


class ScoreReaderXml:
    def __init__(self, log):
        self._log = log
        self._filepath = None

    def refresh_xml(self, xml_path):
        self._filepath = xml_path

    def read_score(self) -> ScoreData:
        assert self._filepath is not None
        score = read_scores_from_xml(self._filepath)
        return ScoreData(score=score)

    def close(self):
        pass


@dataclasses.dataclass
class CricketGameScore:
    runs: typing.Optional[int]
    wickets: typing.Optional[int]
    overs: typing.Optional[int]
    first_innings: typing.Optional[int]

    def __init__(self):
        pass


def parse_int_else_zero(text):
    try:
        return int(text)
    # ValueError if string for example can't parse as int
    # TypeError if value was empty and text parameter is None
    except Exception:
        return 0


def _read_scores_from_xml(filepath) -> CricketGameScore:
    scores = CricketGameScore()
    with open(filepath, "r") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    scoreboard = root.find("scoreboard")
    for e in scoreboard.findall("field"):
        if e.get("key") == "InningsRuns":
            scores.runs = parse_int_else_zero(e.text)
        elif e.get("key") == "InningsWickets":
            scores.wickets = parse_int_else_zero(e.text)
        elif e.get("key") == "InningsCompletedOvers":
            scores.overs = parse_int_else_zero(e.text)
        elif e.get("key") == "FirstInningsScore":
            scores.first_innings = parse_int_else_zero(e.text)
    return scores


def read_scores_from_xml(path) -> bytes:
    scores = _read_scores_from_xml(path)
    # Order is total (runs), wickets, overs, (1st) innings
    # Digits 3, 1, 2, 3 => 9 bytes
    # TODO: proper abstraction for this so it isn't duplicated everywhere
    score_order = [(scores.runs, 3), (scores.wickets, 1), (scores.overs, 2),
                   (scores.first_innings, 3)]
    l = itertools.chain.from_iterable(
        _serialise_score(n, s) for s, n in score_order)
    return bytes(list(l))

# Adapted from https://github.com/Arghnews/cricket_scorer/blob/0e429a527f6e8cf1566b533fb0f1087ecc48758e/src/cricket_scorer/score_handlers/score_reader_excel_impl.py#L32
# If n is none treats it as 0
# For xml parsing this can error, for example if


def _serialise_score(size, n):
    assert size >= 0
    if n is None:
        n = 0
    try:
        n = str(int(n)).zfill(size)
        return [int(n[i * -1]) for i in range(size, 0, -1)]
    except Exception as e:
        return None
