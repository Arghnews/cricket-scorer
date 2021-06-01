from multiprocessing.context import Process
from queue import Queue
import copy
import ctypes
import itertools
import multiprocessing as mp
import io
import logging
import os
import queue
import time

from recordclass import recordclass, make_dataclass
import xlwings as xw

# from .score_reader_excel_helper import Scores
from cricket_scorer.net.packet import Packet

ScoreData = make_dataclass("ScoreData",
        [("digits", int), ("cell", str), ("val", int)], defaults = (0,))

# If able to assume using python 3.6+ (technically 3.7+) then no need for this extra order
SERIALISATION_ORDER = ["total", "wickets", "overs", "innings"]

DEFAULT_CELLS = {
            "total":         ScoreData(digits = 3, cell = "A2"),
            "wickets":       ScoreData(digits = 1, cell = "B2"),
            "overs":         ScoreData(digits = 2, cell = "C2"),
            "innings":       ScoreData(digits = 3, cell = "D2"),
        }

# TODO: uncomment these valid assertions
# if set(serialisation_order) != set(cells.keys()):
#     raise RuntimeError("Spreadsheet cell keys must match:" +
#             str(serialisation_order))
# assert sum(v.digits for v in cells.values()) == Packet.PAYLOAD_SIZE, \
#         "Score digits don't add to packet payload size:" + \
#         str(Packet.PAYLOAD_SIZE)

def loop_de_loop(*args):
    while True:
        time.sleep(1)
        print("Hi from multiprocess")

class ScoresData:
    def __init__(self) -> None:
        self._lock = mp.Lock()
        self._score = bytes(Packet.PAYLOAD_SIZE)
        self._error_msg = ""
    def set(self, score, error_msg):
        assert isinstance(score, bytes)
        assert len(score) == len(self._score)
        with self._lock:
            self._score = score
            self._error_msg = error_msg
    def get(self):
        with self._lock:
            return self._score, self._error_msg

# This is what the main thread talks through
class Reader:
    def __init__(self, logger) -> None:
        self._log = logger
        self._started = False

        self._log.debug("Reader 1")

        self._update_flag = mp.Event()
        self._done_flag = mp.Event()
        self._update_lock = mp.Lock()
        self._scores_data = ScoresData()

        self._spreadsheet_path = mp.Array(ctypes.c_char, 2048, lock=False)
        self._sheet = mp.Array(ctypes.c_char, 256, lock=False)
        self._total_cell = mp.Array(ctypes.c_char, 64, lock=False)
        self._wickets_cell = mp.Array(ctypes.c_char, 64, lock=False)
        self._overs_cell = mp.Array(ctypes.c_char, 64, lock=False)
        self._innings_cell = mp.Array(ctypes.c_char, 64, lock=False)

        # self._spreadsheet_path = mp.Value(ctypes.c_wchar_p, lock=False)
        # self._sheet = mp.Value(ctypes.c_wchar_p, lock=False)
        # self._total_cell = mp.Value(ctypes.c_wchar_p, lock=False)
        # self._wickets_cell = mp.Value(ctypes.c_wchar_p, lock=False)
        # self._overs_cell = mp.Value(ctypes.c_wchar_p, lock=False)
        # self._innings_cell = mp.Value(ctypes.c_wchar_p, lock=False)

        self._log.debug("Reader 2")

        self._p = mp.Process(target=score_reader_excel, args=(
            self._log,
            self._update_flag,
            self._done_flag,
            self._update_lock,
            self._scores_data,
            self._spreadsheet_path,
            self._sheet,
            self._total_cell,
            self._wickets_cell,
            self._overs_cell,
            self._innings_cell,
        ))

        # self._p = mp.Process(target=loop_de_loop, args=(
        #     self._log,
        #     self._update_flag,
        #     self._done_flag,
        #     self._update_lock,
        #     self._scores_data,
        #     self._spreadsheet_path,
        #     self._sheet,
        #     self._total_cell,
        #     self._wickets_cell,
        #     self._overs_cell,
        #     self._innings_cell,
        # ))

        self._log.debug("Reader 3")

        self._p.start()
        self._log.info("Reader initialised")

    def close(self):
        self._log.info("Reader closing")
        self._done_flag.set()
        self._update_flag.set()
        self._p.join()

    def started(self):
        return self._started

    def start(self, settings: dict):
        self._log.debug("Reader start method")
        self._started = True
        self._log.info(settings)
        assert set(settings.keys()) == {"spreadsheet", "sheet", "total", "wickets",
                                        "overs", "innings"}
        self._log.debug("Getting update lock")
        with self._update_lock:
            self._log.debug("Got update lock")
            self._spreadsheet_path.value = settings["spreadsheet"].encode()
            self._sheet.value = settings["sheet"].encode()
            self._total_cell.value = settings["total"].encode()
            self._wickets_cell.value = settings["wickets"].encode()
            self._overs_cell.value = settings["overs"].encode()
            self._innings_cell.value = settings["innings"].encode()
            self._log.debug("Read values from settings, setting update_flag")
            self._update_flag.set()
        self._log.debug("Done with reader start")

    def get(self):
        # self._log.debug("Get called")
        assert self.started()
        return self._scores_data.get()

# class Reader:
#     def __init__(self, logger, scores_data: ScoresData) -> None:
#         self.log = logger

#         self._in_lock = mp.Lock()
#         self._start = mp.Event()
#         self._in_params = {
#             "spreadsheet":          r"C:\Users\justin\cricket.xlsx",
#             "sheet":                "Sheet1",
#             "total":                ScoreData(digits=3, cell="A2"),
#             "wickets":              ScoreData(digits=1, cell="B2"),
#             "overs":                ScoreData(digits=2, cell="C2"),
#             "innings":              ScoreData(digits=3, cell="D2"),
#             "serialisation_order":  ["total", "wickets", "overs", "innings"],
#         }
#         self._spreadsheet = None

#         self._scores_data = scores_data

#         self._started = False

#         self._close = mp.Value(ctypes.c_bool)
#         self._close.value = False

#         self._q = mp.Queue()

#         self._p = mp.Process(target=score_reader_excel, args=(self, self._q))

#         self._p.start()

#     def started(self):
#         return self._started

#     def is_closed(self):
#         return self._close.value

#     def close(self):
#         # with self._close.get_lock():
#         self._close.value = True
#         self._start.set()
#         print("Joining smoining")
#         print(self._p.is_alive())
#         self._p.join()
#         print("I've joined!")

#     def _freeze_params(self, settings: dict):
#         # I'm not sure how python's reference-esque semantics work out as to whether this is
#         # necessary. The mp.Process holds a reference to self._in_params_last_used.
#         # However if I write the line:
#         # self._in_params_last_used = copy.deepcopy(self._in_params)
#         # I'm unsure if this sets the reference the mp.Process has to self._in_params_last_used
#         # to the new value, I believe it just sets this class' reference to the copy.
#         # Hence this should get around it by changing the dict itself that is referred
#         # to by both refs.
#         # self._in_params.clear()
#         # self._in_params.update(copy.deepcopy(settings))
#         self._in_params["spreadsheet"] = settings["spreadsheet"]
#         self._in_params["sheet"] = settings["sheet"]
#         self._in_params["serialisation_order"] = settings["serialisation_order"]
#         for k in settings["serialisation_order"]:
#             self._in_params[k].cell = settings[k]

#     def update_score(self):
#         """Updates cells in sheet
#         Returns error_msg, empty string if none"""
#         score_bytes, error_msg = bytes(Packet.PAYLOAD_SIZE), ""
#         with self._in_lock:
#             unparsable_score_names = []
#             scores = self._in_params["serialisation_order"]
#             for score_name in scores:
#                 score_name, score_data = score_name, self._in_params[score_name]
#                 assert isinstance(score_data, ScoreData)
#                 # Read the cell value from the spreadsheet
#                 cell_value = self._spreadsheet[self._in_params["sheet"]].range(
#                     score_data.cell).value

#                 # Only update the score value if it is serialisable ie. valid
#                 if serialise_score(score_data.digits, cell_value) is None:
#                     unparsable_score_names.append(score_name)
#                 else:
#                     score_data.val = cell_value

#             score_bytes = bytes(itertools.chain.from_iterable(
#                 serialise_score(score_data.digits, score_data.val)
#                 for score_data in [self._in_params[score] for score in scores]
#                 ))

#             error_msg = ""
#             if len(unparsable_score_names) > 0:
#                 error_msg = "Could not parse " + ", ".join(unparsable_score_names)

#         self._scores_data.set(score_bytes, error_msg)
    
#     def get(self):
#         return self._scores_data.get()

#     def start(self, settings: dict):
#         assert set(["spreadsheet", "sheet", "total", "wickets",
#                    "overs", "innings", "serialisation_order"]).issubset(settings.keys())
#         with self._in_lock:
#             self._freeze_params(settings)
#         self._start.set()

#     def _reset(self):
#         with self._in_lock:
#             if self.started():
#                 self._spreadsheet.close()
#             else:
#                 self._started = True
#             self._spreadsheet = xw.Book(self._in_params["spreadsheet"])
#         self._start.clear()

# def update_cells(sheet, keys, params):
#     """Updates cells in sheet
#     Returns error_msg, empty string if none"""
#     unparsable_score_names = []
#     for score_name in keys:
#         assert score_name in params
#         score_name, score_data = score_name, params[score_name]
#         assert isinstance(score_data, ScoreData)
#         # Read the cell value from the spreadsheet
#         cell_value = sheet.range(score_data.cell).value

#         if serialise_score(score_data.digits, cell_value) is None:
#             unparsable_score_names.append(score_name)
#         else:
#             score_data.val = cell_value

#     error_msg = ""
#     if len(unparsable_score_names) > 0:
#         error_msg = "Could not parse " + ", ".join(unparsable_score_names)
#     return error_msg

class SpreadsheetWrapper:
    def __init__(self, scores_data) -> None:
        self._spreadsheet = None
        self._sheet = None
        self._cells = copy.deepcopy(DEFAULT_CELLS)

        self._started = False
        self._scores_data = scores_data

    # TODO: figure out linting
    def update(self, spreadsheet_path, sheet, total_cell, wickets_cell, overs_cell, innings_cell):
        print("Spreadsheet wrapper - update")
        if self._started:
            print("Spreadsheet wrapper - already started, closing prior")
            self._spreadsheet.close()
        print("Spreadsheet wrapper - opening excelwings book")
        self._spreadsheet = xw.Book(spreadsheet_path)
        print("Spreadsheet wrapper - assigning sheet")
        self._sheet = sheet
        for key, val in zip(self._cells.keys(), [total_cell, wickets_cell, overs_cell, innings_cell]):
            self._cells[key].cell = val
        print("Spreadsheet wrapper - done")

    def read_latest_score(self):
        unparsable_score_names = []
        assert SERIALISATION_ORDER == [c for c in self._cells]
        for score_name, score_data in self._cells.items():
            cell_data = self._spreadsheet.sheets[self._sheet].range(score_data.cell).value

            # Only update the score value if it is serialisable ie. valid
            if serialise_score(score_data.digits, cell_data) is None:
                unparsable_score_names.append(score_name)
            else:
                score_data.val = cell_data

        score_bytes = bytes(itertools.chain.from_iterable(
            serialise_score(score_data.digits, score_data.val)
            for score_data in self._cells.values()
            ))

        error_msg = ""
        if len(unparsable_score_names) > 0:
            error_msg = "Could not parse " + ", ".join(unparsable_score_names)
        
        self._scores_data.set(score_bytes, error_msg)

    def close(self):
        if self._spreadsheet is not None:
            self._spreadsheet.close()

# TODO: either replace this, or move it somewhere more appropriate
class OnlyPrintOnDiff:
    def __init__(self):
        self.buf = io.StringIO()
        self.prev = None
    def print(self, *args, **kwargs):
        print(*args, file = self.buf, **kwargs)
    def print_contents_if_diff(self):
        contents = self.buf.getvalue()

        if contents != self.prev:
            print(contents, end = "")

        self.prev = contents
        self.buf = io.StringIO()

def score_reader_excel(
                log,
                update_flag: mp.Event, done_flag: mp.Event,
                update_lock: mp.Lock,
                scores_data: ScoresData,
                spreadsheet_path: mp.Value, sheet: mp.Value,
                total_cell: mp.Value, wickets_cell: mp.Value,
                overs_cell: mp.Value, innings_cell: mp.Value):

    # Issue TODO. Cleaning closing and atomic updates.
    # If closing is set whilst waiting for a lock
    # Trouble is if closed after check .is_closed and then in update_score (race condition)
    # Might be kind of irrelevant anyway as if the spreadsheet is closed first this
    # whole thing will throw a hissy fit from xlwings

    # log.setLevel(logging.DEBUG)

    print("Testing testing testing testing testing from subprocess!")

    # while True:
    #     time.sleep(1)
    #     print("hi from subprocess")
    #     log.info("hi boys")

    printer = OnlyPrintOnDiff()
    _print = lambda msg, *args, **kwargs: printer.print("[Subprocess] " + str(msg), *args, **kwargs)

    spreadsheet = SpreadsheetWrapper(scores_data)
    _print("Spreadsheet init, waiting on update flag")
    try:
        update_flag.wait()
        while not done_flag.is_set():
            if update_flag.is_set():
                _print("Update flag set")
                with update_lock:
                    _print("Calling spreadsheet.update")

                    strings_as_bytes = [spreadsheet_path.value, sheet.value,
                                       total_cell.value, wickets_cell.value,
                                       overs_cell.value, innings_cell.value]
                    _print("Strings:", strings_as_bytes)
                    strings = [s.decode() for s in strings_as_bytes]
                    _print("Strings as strings:", strings)
                    spreadsheet.update(*strings)
                    update_flag.clear()
                    _print("Update flag cleared")
            else:
                _print("Reading latest score")
                spreadsheet.read_latest_score()
            printer.print_contents_if_diff()

    except Exception as e:
        print("[Subprocess] Closing spreadsheet, exception raised:", str(e))
        spreadsheet.close()
        raise

    print("[Subprocess] Done")

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
            #  "innings":  ScoreData(digits = 3, cell = "D2"),
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
