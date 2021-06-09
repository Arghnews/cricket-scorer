import cricket_scorer.net.countdown_timer as timer
from . import score_reader_excel_impl

class SpreadsheetWrapperDummy:
    def __init__(self):
        self._cells = {}
        self._timer = timer.make_countdown_timer(seconds = 5)
    def reinit(self, spreadsheet_path, worksheet):
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
    return score_reader_excel_impl.ScoreReaderExcel(SpreadsheetWrapperDummy,
            logger)
