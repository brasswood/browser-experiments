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

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    google = lib.get_resource("google.png")
    init_page =  "about:blank" if do_baseline else "outlook.office365.com"
    folder = lib.get_resource("experiment_folder.png")
    margin = lib.get_resource("message_margin.png")
    nothing_selected = lib.get_resource("nothing_selected.png")
    with ctx.monitor("chromium"), ctx.start_app(["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", init_page]):
        if do_baseline:
            try:
                pyautogui.locateOnScreen(str(google))
                raise Exception("error: set startup page to about:blank")
            except ImageNotFoundException:
                pass
            # wait 30 on the blank page
            time.sleep(30)
            ctx.screenshot("blank.png")
            # navigate to outlook
            lib.load_page("chromium", 'outlook.office365.com')
        time_remaining = 30
        point, t = lib.locate_center_time(folder, time_remaining)
        time_remaining -= t
        pyautogui.click(*point)

        _point, t = lib.locate_center_time(nothing_selected, time_remaining)
        time_remaining -= t

        (x, y), t = lib.locate_center_time(margin, time_remaining)
        time_remaining -= t
        pyautogui.moveTo(x+100, y+25)
        pyautogui.click(x+100, y+25)

        time.sleep(time_remaining)
        ctx.screenshot("app.png")

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__), True)
