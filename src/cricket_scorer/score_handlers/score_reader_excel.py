import itertools
import os
import multiprocessing as mp

from recordclass import recordclass, make_dataclass
import xlwings as xw

# from .score_reader_excel_helper import Scores
from cricket_scorer.net.packet import Packet

ScoreData = make_dataclass("ScoreData",
        [("digits", int), ("cell", str), ("val", int)], defaults = (0,))

serialisation_order = ["total", "wickets", "overs", "1st innings"]

default_cells = {
            "total":         ScoreData(digits = 3, cell = "A2"),
            "wickets":       ScoreData(digits = 1, cell = "B2"),
            "overs":         ScoreData(digits = 2, cell = "C2"),
            "1st innings":   ScoreData(digits = 3, cell = "D2"),
        }

class ScoreReaderExcel:
    def __init__(self, log) -> None:
        self.active: bool = False
        self.log = log
        self.q = mp.Queue()
        self.p = mp.Process(target=f, args=(self.log, self.q,))
    def start(self, spreadsheet_path, sheet, cells = default_cells,
        error_message_cell = None):
        self.active = True
        self.p.start()

def f(q: mp.Queue, log, spreadsheet_path, sheet, cells = default_cells,
        error_message_cell = None):

    log.info("Using spreadsheet at:", os.path.realpath(spreadsheet_path))
    workbook = xw.Book(spreadsheet_path)
    sheet = workbook.sheets[sheet]
    last_val = None
    while True:
        unparsable_score_names = []
        for score_name, score_data in cells.items():
            # Read the cell value from the spreadsheet
            cell_value = sheet.range(score_data.cell).value

            if serialise_score(score_data.digits, cell_value) is None:
                unparsable_score_names.append(score_name)
            else:
                score_data.val = cell_value

        if error_message_cell:
            update_error_message_cell(sheet, error_message_cell,
                    unparsable_score_names)

        # yield bytes(itertools.chain.from_iterable(
        val = bytes(itertools.chain.from_iterable(
            serialise_score(score_data.digits, score_data.val)
            for score_data in [cells[key] for key in serialisation_order]
            ))
        if val != last_val:
            q.put(val)

    # for i in score_reader_excel(*args):
        # q.put(i)

def score_reader_excel(log, spreadsheet_path, sheet, cells = default_cells,
        error_message_cell = None):

    # TODO: uncomment these valid assertions
    # if set(serialisation_order) != set(cells.keys()):
    #     raise RuntimeError("Spreadsheet cell keys must match:" +
    #             str(serialisation_order))
    # assert sum(v.digits for v in cells.values()) == Packet.PAYLOAD_SIZE, \
    #         "Score digits don't add to packet payload size:" + \
    #         str(Packet.PAYLOAD_SIZE)

    log.info("Using spreadsheet at:", os.path.realpath(spreadsheet_path))
    workbook = xw.Book(spreadsheet_path)
    sheet = workbook.sheets[sheet]
    while True:
        unparsable_score_names = []
        for score_name, score_data in cells.items():
            # Read the cell value from the spreadsheet
            cell_value = sheet.range(score_data.cell).value

            if serialise_score(score_data.digits, cell_value) is None:
                unparsable_score_names.append(score_name)
            else:
                score_data.val = cell_value

        if error_message_cell:
            update_error_message_cell(sheet, error_message_cell,
                    unparsable_score_names)

        yield bytes(itertools.chain.from_iterable(
            serialise_score(score_data.digits, score_data.val)
            for score_data in [cells[key] for key in serialisation_order]
            ))

# This function is NOT required, but may be helpful for printing parsing
# errors to the spreadsheet
def update_error_message_cell(sheet, error_message_cell,
        unparsable_score_names):
    # If any score cells could not be parsed they will be in this list
    sheet.range(error_message_cell).value = ""
    if len(unparsable_score_names) > 0:
        sheet.range(error_message_cell).value = \
                "Could not parse " + ", ".join(unparsable_score_names)

def serialise_score(size, n):
    try:
        n = str(int(n)).zfill(size)
        return [int(n[i * -1]) for i in range(size, 0, -1)]
    except Exception as e:
        return None

#  def main():
    #  while True:
        #  # Read score somehow from excel
        #  score = xlwings.get_score_from_excel()
        #  yield score

#  class ScoreReaderExcel:
    #  def __init__(self, log, spreadsheet, workbook, cells):

        #  self.log = log

        #  self.log.info("Example log message")

        #  # Relative path to spreadsheet, this uses spreadsheet in current directory, intended for script to be run from cricket_scorer directory
        #  #  path_to_spreadsheet = r"cricket.xlsx"
        #  path_to_spreadsheet = r"C:\Users\justin\code\cricket_scorer\cricket.xlsx"
        #  # Altnerative absolute path
        #  # path_to_spreadsheet = r"C:\Users\Ewan\Documents\cricket_scoring_stuff\cricket_scorer\cricket.xlsx"

        #  self.log.info("Using spreadsheet at:", path_to_spreadsheet, "- full path:", os.path.realpath(path_to_spreadsheet))
        #  self.workbook = xw.Book(path_to_spreadsheet)

        #  self.sheet = self.workbook.sheets["Sheet1"]

        #  # The order of these lines is the order in which they are serialised
        #  self.scores = Scores(self.sheet, {
            #  "total":        ScoreData(digits = 3, cell = "A2"),
            #  "wickets":      ScoreData(digits = 1, cell = "B2"),
            #  "overs":        ScoreData(digits = 2, cell = "C2"),
            #  "1st innings":  ScoreData(digits = 3, cell = "D2"),
        #  })

    #  # Called periodically when the program is ready to send a score update.
    #  # Returns new score. Will only send if score has changed.
    #  def __call__(self):

        #  # Update the scores. Returns any score cells that could not be parsed
        #  unparsable_score_names = self.scores.update_scores()

        #  # Example - Update a cell in the spreadsheet with unparsable cells
        #  self.update_error_message_cell("E3", unparsable_score_names)

        #  # Example - Write the date and time to the spreadsheet
        #  self.sheet.range("E2").value = str(datetime_near_now())

        #  # Serialise the scores and return. Required
        #  return self.scores.serialise_scores()

    #  # This function is NOT required, but may be helpful for printing parsing
    #  # errors to the spreadsheet
    #  def update_error_message_cell(self, error_message_cell, unparsable_score_names):
        #  # If any score cells could not be parsed they will be in this list
        #  self.sheet.range(error_message_cell).value = ""
        #  if len(unparsable_score_names) > 0:
            #  self.sheet.range(error_message_cell).value = "Could not parse " + ", ".join(unparsable_score_names)
