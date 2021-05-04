import os

import xlwings as xw

from .score_reader_excel_helper import Scores, ScoreData, datetime_near_now

class ScoreReaderExcel:
    def __init__(self, log):
        self.log = log

        self.log.info("Example log message")

        # Relative path to spreadsheet, this uses spreadsheet in current directory, intended for script to be run from cricket_scorer directory
        #  path_to_spreadsheet = r"cricket.xlsx"
        path_to_spreadsheet = r"C:\Users\justin\code\cricket_scorer\cricket.xlsx"
        # Altnerative absolute path
        # path_to_spreadsheet = r"C:\Users\Ewan\Documents\cricket_scoring_stuff\cricket_scorer\cricket.xlsx"

        self.log.info("Using spreadsheet at:", path_to_spreadsheet, "- full path:", os.path.realpath(path_to_spreadsheet))
        self.workbook = xw.Book(path_to_spreadsheet)

        self.sheet = self.workbook.sheets["Sheet1"]

        # The order of these lines is the order in which they are serialised
        self.scores = Scores(self.sheet, {
            "total":        ScoreData(digits = 3, cell = "A2"),
            "wickets":      ScoreData(digits = 1, cell = "B2"),
            "overs":        ScoreData(digits = 2, cell = "C2"),
            "1st innings":  ScoreData(digits = 3, cell = "D2"),
        })

    # Called periodically when the program is ready to send a score update.
    # Returns new score. Will only send if score has changed.
    def __call__(self):

        # Update the scores. Returns any score cells that could not be parsed
        unparsable_score_names = self.scores.update_scores()

        # Example - Update a cell in the spreadhseet with unparsable cells
        self.update_error_message_cell("E3", unparsable_score_names)

        # Example - Write the date and time to the spreadsheet
        self.sheet.range("E2").value = str(datetime_near_now())

        # Serialise the scores and return. Required
        return self.scores.serialise_scores()

    # This function is NOT required, but may be helpful for printing parsing errors to the spreadsheet
    def update_error_message_cell(self, error_message_cell, unparsable_score_names):
        # If any score cells could not be parsed they will be in this list
        self.sheet.range(error_message_cell).value = ""
        if len(unparsable_score_names) > 0:
            self.sheet.range(error_message_cell).value = "Could not parse " + ", ".join(unparsable_score_names)
