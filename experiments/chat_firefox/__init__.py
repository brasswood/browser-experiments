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
from ..lib import Experiment, Context
from .. import lib

def run_experiment(ex: Context) -> None:
    with ex:
        button2 = lib.get_resource("2.png")
        ex.start_monitor("firefox")
        ex.start(["firefox", "-P", "Experiments", "about:blank"])
        # wait 30 on the blank page
        time.sleep(30)
        ex.screenshot("blank.png")
        # navigate to mov.im/chat
        # unfortunately, the type stub incorrectly says that minSearchTime is a required argument for the following line
        ex.load_page("firefox", 'mov.im/chat')
        # start a timer
        start = time.time()
        # try to click Open Hardware Chat, waiting up to 10 seconds for the page to load
        while True:
            try:
                point = pyautogui.locateCenterOnScreen(str(button2), minSearchTime=0, confidence=0.9)
                assert point is not None
                (x, y) = point
                pyautogui.click(x, y)
                break
            except ImageNotFoundException:
                if time.time() - start >= 10:
                    raise
        # sit for the remaining time out of 30 seconds since navigating to chat
        time.sleep(30 - (time.time() - start))
        ex.screenshot("app.png")

def main() -> None:
    with Experiment.parse_sysargs() as ex:
        run_experiment(ex)
