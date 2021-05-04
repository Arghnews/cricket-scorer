#!/usr/bin/env python3

import os

import PySimpleGUI as sg

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

layout = [  [sg.Text('Filename')],
            [sg.Input(), sg.FileBrowse(initial_folder = initial, file_types = extensions)],
            [sg.OK(), sg.Cancel()]]

# layout =  [[sg.Button('Ok'), sg.Button('Cancel')]]

# layout =  [[sg.FileBrowse()]]

window = sg.Window('Get filename example', layout)

event, values = window.read()

print(event, values)

print("Selected file at", values["Browse"])

window.close()

