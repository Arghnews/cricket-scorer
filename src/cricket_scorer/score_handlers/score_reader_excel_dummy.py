import cricket_scorer.net.countdown_timer as timer
from . import score_reader_excel_impl


class SpreadsheetWrapperDummy:
    """Dummy Excel Spreadsheet wrapper for testing on systems without Excel"""
    def __init__(self):
        self._cells = {}
        self._timer = timer.make_countdown_timer(seconds=5)

    def reinit(self, *args):
        pass

    def read_cell_value(self, cell_score_data):
        self._cells.setdefault(cell_score_data.cell, 0)
        if self._timer.just_expired():
            self._cells[cell_score_data.cell] += 1
            self._timer.reset()
        return self._cells[cell_score_data.cell]

    def close(self):
        pass


def get_score_reader(logger):
    """Returns a dummy Excel score reader instance"""
    return score_reader_excel_impl.ScoreReaderExcel(SpreadsheetWrapperDummy, logger)
