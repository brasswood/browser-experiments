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
from ..lib import Context
from .. import lib

def run_experiment(ctx: Context) -> None:
    button2 = lib.get_resource("open_hw_chat_button.png")
    google = lib.get_resource("google.png")
    with ctx.monitor("chromium"), ctx.start_app(["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", "about:blank"]):
        try:
            pyautogui.locateOnScreen(str(google))
            raise Exception("error: set startup page to about:blank")
        except ImageNotFoundException:
            pass
        # wait 30 on the blank page
        time.sleep(30)
        ctx.screenshot("blank.png")
        # navigate to mov.im/chat
        lib.load_page("chromium", 'mov.im/chat')
        start = time.time()
        # try to click Open Hardware Chat, waiting up to 10 seconds for the page to load
        point = pyautogui.locateCenterOnScreen(str(button2), minSearchTime=10, confidence=0.9)
        assert point is not None
        (x, y) = point
        pyautogui.click(x, y)
        # sit for the remaining time out of 30 seconds since navigating to chat
        time.sleep(30 - (time.time() - start))
        ctx.screenshot("app.png")

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__))
