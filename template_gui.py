#!/usr/bin/env python3

import asyncio
import io
import os

import time

import PySimpleGUI as sg

# This will be either reading from the excel spreadsheet via xlwings
# Or from the I2C ports
# Or just prints out numbers as a dummy generator
def score_reader_f():
    for num in range(1000000):
        #  print("Getting net num", num)
        yield num

# This will be the networking code function that control will be handed to that
# will send it to the other scoreboard
async def score_sender_func():
    #  print("score sender started")
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
    print("Using settings file:", user_settings_file.get_filename())

    settings = {
            "spreadsheet": r"C:\Users\justin\cricket.xlsx",
            #  "spreadsheet_selector": r"C:\Users\justin\cricket.xlsx",
            "sheet": "Sheet1",
            "total": "A2",
            "wickets": "B2",
            "overs": "C2",
            "innings": "D2",
            "error_cell": "E3",
            "enable_error_cell": False,
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
                        initial_folder = settings["spreadsheet"],
                        file_types = extensions),
                    sg.Text(settings["spreadsheet"], auto_size_text = True,
                        size = (80, 1), key = "spreadsheet_text")
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

                [sg.Checkbox("Enable error cell",
                    default = settings["enable_error_cell"],
                    key = "enable_error_cell"),
                    #  sg.Text("Error cell:", key = "error_cell_label"),
                    sg.Input(settings["error_cell"], size = (7, 1),
                        key = "error_cell",
                        visible = settings["enable_error_cell"]),
                    ],

                [sg.Button("Run", enable_events = True, key = "run"),
                    sg.Text(size = (40, 1), auto_size_text = True,
                        key = "run_label"), sg.Save()],
                #  [sg.Button("Run/Reload", key = "reload")],
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

    score_reader = score_reader_f()
    score_sender = score_sender_func()
    await score_sender.asend(None)

    last_values = None
    printer = OnlyPrintOnDiff()
    _print = lambda *args, **kwargs: printer.print(*args, **kwargs)

    while True:
        event, values = window.read(timeout = 50)
        if not values["spreadsheet_selector"]:
            values["spreadsheet_selector"] = settings["spreadsheet"]

        if event == "Save":
            #  user_settings_file["spreadsheet"] = spreadsheet
            #  settings.pop("spreadsheet_selector", None)
            for k, v in values.items():
                if isinstance(v, str) and v:
                    settings[k] = v
                else:
                    settings[k] = v
            _print("Saving settings", settings)

            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])

            user_settings_file.write_new_dictionary(settings)
        if event == "Quit" or event == sg.WIN_CLOSED:
            break

        if event == "run":
            _print("Run")
            _print(settings)
            _print(values)
            s = set(values.keys()) & set(settings.keys())
            _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])
            pass

        _print(event, values)

        #  _print(window.key_dict)
        #  return

        score = next(score_reader)
        #  score = await score_reader
        #  _print("Back in main loop", score)
        await score_sender.asend(score)

        # Update gui
        if values["spreadsheet_selector"]:
            window["spreadsheet_text"].update(values["spreadsheet_selector"])
            settings["spreadsheet"] = values["spreadsheet_selector"]
        window["error_cell"].update(visible = values["enable_error_cell"])

        #  _print(settings)
        #  _print(values)
        s = set(values.keys()) & set(settings.keys())
        _print([(k, settings[k], values[k]) for k in s if values[k] != settings[k]])
        if any(True for k in s if values[k] != settings[k]):
        #  if values != settings:
            _print("Updating")
            window["run_label"].update("Config changed. Click Run to reload",
                    visible = True)
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
        last_values = values
        printer.print_contents_if_diff()
        #  printer = OnlyPrintOnDiff(printer)
    #  print("Selected file at", values["Browse"])

    window.close()

iol = asyncio.get_event_loop()
iol.run_until_complete(main())

