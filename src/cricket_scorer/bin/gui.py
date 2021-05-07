#!/usr/bin/env python3

import asyncio
import os

import PySimpleGUI as sg

# This will be either reading from the excel spreadsheet via xlwings
# Or from the I2C ports
# Or just prints out numbers as a dummy generator
def score_reader_f():
    for num in range(5):
        print("Getting net num", num)
        yield num

# This will be the networking code function that control will be handed to that
# will send it to the other scoreboard
async def score_sender_func():
    print("score sender started")
    while 1:
        print("score sender start iter")
        val = (yield)
        print("Sending", val, "to scoreboard")

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

    layout = [[sg.Text('Spreadsheet')],
              [sg.Input(),
                  sg.FileBrowse(
                      initial_folder = initial, file_types = extensions)],
              [sg.OK(), sg.Cancel()]]

    # layout =  [[sg.Button('Ok'), sg.Button('Cancel')]]

    # layout =  [[sg.FileBrowse()]]

    window = sg.Window('Cricket Scorer - Spreadsheet selector', layout)

    score_reader = score_reader_f()
    score_sender = score_sender_func()
    await score_sender.asend(None)

    while True:
        event, values = window.read(timeout = 100)
        print(event, values)

        score = next(score_reader)
        print("Back in main loop", score)
        await score_sender.asend(score)
        # Update gui

        if event == 'Cancel' or event == sg.WIN_CLOSED:
            break

    print("Selected file at", values["Browse"])

    window.close()

iol = asyncio.get_event_loop()
iol.run_until_complete(main())

