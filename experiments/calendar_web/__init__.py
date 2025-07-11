# Copyright 2025 Andrew Riachi
# This file is part of brasswood/browser-experiments.
# brasswood/browser-experiments is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import time
import pyautogui
from pyautogui import ImageNotFoundException
from ..lib import Experiment
from .. import lib

def run_experiment(ex: Experiment) -> None:
    with ex:
        button1 = lib.get_resource("1.png")
        google = lib.get_resource("google.png")
        ex.start_monitor("chromium")
        ex.start(["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", "about:blank"])
        try:
            pyautogui.locateOnScreen(str(google))
            raise Exception("error: set startup page to about:blank")
        except ImageNotFoundException:
            pass
        # wait 30 on the blank page
        time.sleep(30)
        ex.screenshot("blank.png")
        # navigate to google calendar
        point = pyautogui.locateCenterOnScreen(str(button1), minSearchTime=0, confidence=0.9)
        assert point is not None
        (x, y) = point
        pyautogui.tripleClick(x=x+100, y=y)
        pyautogui.write('calendar.google.com')
        pyautogui.press('enter')
        # wait another 30
        time.sleep(30)
        ex.screenshot("app.png")

def main() -> None:
    run_experiment(Experiment.parse_sysargs())
