import xlwings as xw

from . import score_reader_excel_impl

class SpreadsheetWrapper:
    def __init__(self):
        self._spreadsheet = None
        pass
    def reinit(self, spreadsheet_path, worksheet):
        self._spreadsheet = xw.Book(spreadsheet_path)
        self._worksheet = worksheet
    def read_cell_value(self, cell_score_data):
        return self._spreadsheet.sheets[self._worksheet].range(
                cell_score_data.cell).value
    def close(self):
        if self._spreadsheet is not None:
            self._spreadsheet.close()

def get_score_reader(logger):
    return score_reader_excel_impl.ScoreReaderExcel(SpreadsheetWrapper, logger)
