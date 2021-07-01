import copy
import itertools
import sys

from cricket_scorer.net.packet import Packet
import cricket_scorer.score_handlers.utils

from dataclasses import dataclass


@dataclass
class ScoreData:
    """Class for holding Excel score state"""
    digits: int
    cell: str
    val: int = 0


# If able to assume using python 3.6+ (technically 3.7+) then no need for this extra order
# Cpython impl detail as of 3.6. Required as of 3.7. We assert this for now
assert sys.version_info.major >= 3 and sys.version_info.minor >= 6
SERIALISATION_ORDER = ["total", "wickets", "overs", "innings"]

DEFAULT_CELLS = {
    "total": ScoreData(digits=3, cell="A2"),
    "wickets": ScoreData(digits=1, cell="B2"),
    "overs": ScoreData(digits=2, cell="C2"),
    "innings": ScoreData(digits=3, cell="D2"),
}


def _serialise_score(size, n):
    try:
        n = str(int(n)).zfill(size)
        return [int(n[i * -1]) for i in range(size, 0, -1)]
    except Exception as e:
        return None


class ScoreReaderExcel:
    """Class that uses a SpreadsheetClass given on construction to interface
    with a Microsoft Excel spreadsheet to read values from cells corresponding
    to scores and return the latest valid scores via self.read_score()
    """
    def __init__(self, SpreadsheetClass, logger):
        self._log = logger
        self._spreadsheet = SpreadsheetClass()
        self._cells = copy.deepcopy(DEFAULT_CELLS)

        self._score_bytes = bytes(Packet.PAYLOAD_SIZE)
        self._error_msg = ""

        self._running = False

    def refresh_excel(self, spreadsheet_path, worksheet, total_cell, wickets_cell, overs_cell,
                      innings_cell):
        self._log.debug("Spreadsheet wrapper - update")
        if self._running:
            self._log.debug("Spreadsheet wrapper - already started, closing prior")
            self._spreadsheet.close()
        self._running = True
        self._log.debug("Spreadsheet wrapper - opening excelwings book")
        self._spreadsheet.reinit(self._log, spreadsheet_path, worksheet)
        for key, val in zip(self._cells.keys(),
                            [total_cell, wickets_cell, overs_cell, innings_cell]):
            self._cells[key].cell = val
        self._log.debug("Spreadsheet wrapper - done refreshing")

    def read_score(self):
        assert SERIALISATION_ORDER == list(self._cells.keys())
        unparsable_score_names = []
        for score_name, score_data in self._cells.items():
            cell_data = self._spreadsheet.read_cell_value(score_data)

            # Only update the score value if it is serialisable ie. valid
            if _serialise_score(score_data.digits, cell_data) is None:
                unparsable_score_names.append(score_name)
            else:
                score_data.val = cell_data

        self._score_bytes = bytes(
            itertools.chain.from_iterable(
                _serialise_score(score_data.digits, score_data.val)
                for score_data in self._cells.values()))

        self._error_msg = ""
        if len(unparsable_score_names) > 0:
            self._error_msg = "Could not parse " + ", ".join(unparsable_score_names)

        return cricket_scorer.score_handlers.scoredata.ScoreData(score=self._score_bytes,
                                                                 error_msg=self._error_msg)

    def close(self):
        if self._spreadsheet is not None:
            self._spreadsheet.close()
        self._running = False
