import PySimpleGUI as sg
from helpers.icon import SCISSORS_ICON
from helpers.version import CURRENT, CHANGES


def open_about_window():
    about_layout = [
        [sg.Text("Clippy", font=("Arial", 20))],
        [sg.Text("Video clipper tool powered by FFMPEG.")],
        [sg.Text("Made by hako")],
        [sg.Push()],
        [sg.Text(f"Version {CURRENT}")],
        [sg.Text(f"Changes: {CHANGES}")],
        [sg.Push()],
        [sg.Text("Special thanks:\nDatEati\nLelDoge"), sg.Push(), sg.Text(":    |")],
    ]

    about_window = sg.Window(
        "About Clippy", about_layout, icon=SCISSORS_ICON, finalize=True
    )

    while True:
        event, values = about_window.read()
        if event == sg.WIN_CLOSED:
            break
