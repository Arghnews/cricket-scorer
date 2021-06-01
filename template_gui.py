#!/usr/bin/env python3

import asyncio
import io
import os

import time

import PySimpleGUI as sg

from cricket_scorer.misc import params
from cricket_scorer.net import connection
from cricket_scorer.score_handlers.score_reader_excel import Reader

import copy
import ctypes
import multiprocessing as mp

# This will be either reading from the excel spreadsheet via xlwings
# Or from the I2C ports
# Or just prints out numbers as a dummy generator
def score_reader_f(*args):
    print("score_reader_f sender started with args:", *args)
    for num in range(1000000):
        # print("Getting net num", num)
        epoch_time = int(time.time()) // 5
        yield bytes([epoch_time % 10] * 9)

# This will be the networking code function that control will be handed to that
# will send it to the other scoreboard
async def score_sender_func(*args):
    print("score_sender_func started with args:", *args)
    while 1:
        #  print("score sender start iter")
        val = (yield)
        #  print("Sending", val, "to scoreboard")

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

class BetterTimer:
    def __init__(self) -> None:
        self._timers = {}
    def restart(self):
        self._timers.clear()
    def start(self, name):
        total, started = self._timers.setdefault(name, (0, -1))
        assert started == -1, "Must be stopped before starting"
        self._timers[name] = (total, time.time())
    def stop(self, name):
        assert name in self._timers
        total, started = self._timers.get(name)
        assert started != -1, "Must be started before stopped"
        total += time.time() - started
        self._timers[name] = (total, -1)
    def running(self, name):
        return name in self._timers and self._timers[name][1] != -1
    def summary(self):
        for k in self._timers:
            if self.running(k):
                self.stop(k)
        for name, (t, _) in self._timers.items():
            print(name, "->", t)

async def main():
    #  sg.theme('Dark Blue 3')  # please make your creations colorful

    initial = os.path.dirname(os.path.realpath(__file__))

    # https://en.wikipedia.org/wiki/List_of_Microsoft_Office_filename_extensions
    extensions = (
        ("All Excel files", "*.xl*"),
        ("ALL Files", "*.*"),
        ("Excel workbook", "*.xlsx"),
        ("Excel macro-enabled workbook", "*.xlsm"),
        ("Legacy Excel worksheets", "*.xls"),
        ("Legacy Excel macro", "*.xlm"),
        )

    user_settings_file = sg.UserSettings()
    # This seems to NEED to be called to initialise the default filename

    # Printing this in a Windows 8 virtualmachine at least breaks, with module __main__ has
    # no attribute __FILE__ - this works from a file not from a script
    # I think the problem is elsewhere
    # print("Using settings file:", user_settings_file.get_filename())
    # Must set this
    user_settings_file.set_location("cricket-scorer-cache.json")
    print("Using settings file:", user_settings_file.get_filename())

    settings = {
            "spreadsheet": r"C:\Users\justin\cricket.xlsx",
            #  "spreadsheet_selector": r"C:\Users\justin\cricket.xlsx",
            "sheet": "Sheet1",
            "total": "A2",
            "wickets": "B2",
            "overs": "C2",
            "innings": "D2",
            # "serialisation_order": ["total", "wickets", "overs", "innings"],
            }
    settings.update(user_settings_file.read())
    print(settings)

    layout = [
                #  [sg.Text('Spreadsheet')
                    #  ],

                #  [sg.FileBrowse(key = "spreadsheet_selector",
                    #  enable_events = True,
                    #  initial_folder = initial, file_types = extensions)
                    #  ],

                [sg.Text("Spreadsheet:"),
                    sg.FileBrowse(key = "spreadsheet_selector",
                        #  enable_events = True,
                        target = "spreadsheet",
                        initial_folder = os.path.dirname(settings["spreadsheet"]),
                        file_types = extensions),
                    sg.Text(settings["spreadsheet"], auto_size_text = True,
                        size = (80, 1), key = "spreadsheet")
                    ],

                [sg.Text("Workbook name:"), sg.Input(settings["sheet"],
                    key = "sheet")
                    ],

                [sg.Text("Cell where scores live in spreadsheet:")
                    ],
                [
                    sg.Text("Total:"), sg.Input(settings["total"],
                        size = (7, 1), key = "total"),
                    sg.Text("Wickets:"), sg.Input(settings["wickets"],
                        size = (7, 1), key = "wickets"),
                    sg.Text("Overs:"), sg.Input(settings["overs"],
                        size = (7, 1), key = "overs"),
                    sg.Text("1st Innings:"), sg.Input(settings["innings"],
                        size = (7, 1), key = "innings"),
                    ],

                [sg.Text("", key = "error_msg")],
                # [sg.Checkbox("Enable error cell",
                #     default = settings["enable_error_cell"],
                #     key = "enable_error_cell"),
                #     #  sg.Text("Error cell:", key = "error_cell_label"),
                #     sg.Input(settings["error_cell"], size = (7, 1),
                #         key = "error_cell",
                #         visible = settings["enable_error_cell"]),
                #     ],

                [sg.Button("Run", enable_events = True, key = "run"),
                    sg.Text(size = (50, 1), auto_size_text = True,
                        key = "run_label"), sg.Save()],
                #  [sg.Button("Run/Reload", key = "reload")],
                [sg.Button("Delete saved profile", key = "delete")],
                [sg.Quit(pad = (5, 30))
                    ]
              ]

    #  layout = [[sg.FileBrowse(initial_folder = initial, file_types = extensions)]]

    # layout =  [[sg.Button('Ok'), sg.Button('Cancel')]]

    # layout =  [[sg.FileBrowse()]]

    window = sg.Window('Cricket Scorer - Spreadsheet selector', layout,
            finalize = True,
            size = (800, 600),
            return_keyboard_events = True,
            )

    args = params.sender_profiles["sender_args_excel"]
    # This stinks. Must "remember" not to call args.logger() again it makes a
    # new one and duplicates output
    logger = args.logger()
    make_score_sender = lambda: connection.sender_loop(logger, args)
    score_sender = make_score_sender()
    # score_sender = score_sender_func(args)
    await score_sender.asend(None)

    reader = Reader(logger)

    # score_reader = score_reader_f()
    # make_score_reader = score_reader_excel.score_reader_excel(logger)
    # Initialised after inputs are given in loop
    # score_reader = None

    printer = OnlyPrintOnDiff()
    _print = lambda *args, **kwargs: printer.print(*args, **kwargs)

    saved_settings = copy.deepcopy(settings)

    timer = BetterTimer()
    started = 0

    while True:
        if started == 1:
            print("Restarting timer")
            timer.restart()
            started = 2
        timer.start("loop")
        event, values = window.read(timeout = 10)
        if values["spreadsheet_selector"]:
            values["spreadsheet"] = values["spreadsheet_selector"]
            settings["spreadsheet"] = values["spreadsheet_selector"]

        _print(event)

        if event == "Save":
            #  user_settings_file["spreadsheet"] = spreadsheet
            #  settings.pop("spreadsheet_selector", None)
            # for k, v in values.items():
            # for k, v in [(k, values[k]) for k in settings.keys()]:
            for k in settings.keys():
                if k not in values:
                    continue
                v = values[k]
                if isinstance(v, str) and v:
                    settings[k] = v
                else:
                    settings[k] = v
            _print("Saving settings", settings)

            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])

            user_settings_file.write_new_dictionary(settings)
            saved_settings = copy.deepcopy(settings)

        if event == "Quit" or event == sg.WIN_CLOSED:
            reader.close()
            break

        if event == "run":
            _print("Run")
            _print(settings)
            _print(values)
            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])

            # score_reader = score_reader_excel.score_reader_excel(logger, *score_reader_init_args)
            # reader = Reader(logger, settings)

            # reader.start({k: values[k] for k in settings if k in values})
            _print("Calling reader.start with " + str(settings))
            reader.start(settings)
            started = 1

            # try:
            #     await score_sender.asend(False)
            # except StopAsyncIteration as e:
            #     print("Stopped")
            # score_sender = make_score_sender()
            # await score_sender.asend(None)

        if event == "delete":
            user_settings_file.delete_file()
            saved_settings.clear()
            pass

        _print(event, values)

        timer.start("reader")
        if reader.started():
            timer.start("reader.get")
            score, error_msg = reader.get()
            timer.stop("reader.get")
            window["error_msg"].update(error_msg)
            timer.start("score_sender.asend(score)")
            await score_sender.asend(score)
            timer.stop("score_sender.asend(score)")
        timer.stop("reader")

        # Update gui
        # if values["spreadsheet_selector"]:
        # window["spreadsheet_text"].update(values["spreadsheet_selector"])
        # settings["spreadsheet"] = values["spreadsheet_selector"]

        #  _print(settings)
        #  _print(values)
        s = set(values.keys()) & set(settings.keys())
        _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])
        _print("Settings:", settings)
        _print("Values:", values)
        if saved_settings != settings:
        # if any(True for k in s if values[k] != settings[k]):
        #  if values != settings:
            _print("Updating")
            window["run_label"].update("Config changed. Click \"Run\" to reload, "
                                       "click \"Save\" to save", visible=True)
        else:
            _print("Not showing")
            window["run_label"].update(visible = False)

        #  if values == last_values:
            #  continue

            #  #  _print("Updating!")
            #  #  _print("spreadsheet now:", spreadsheet)
        #  if values["sheet"]:
            #  settings["sheet"] = values["sheet"]
            #  #  _print("spreadsheet now:", spreadsheet)
            #  window["sheet"].update(settings["sheet"])

        #  await asyncio.sleep(1)
        printer.print_contents_if_diff()
        timer.stop("loop")
        #  printer = OnlyPrintOnDiff(printer)
    #  print("Selected file at", values["Browse"])

    timer.summary()

    window.close()

if __name__ == "__main__":
    mp.freeze_support()
    iol = asyncio.get_event_loop()
    iol.run_until_complete(main())
