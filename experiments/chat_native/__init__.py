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
from ..lib import Context
from .. import lib

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    chat_icon = lib.get_resource("open_hw_chat_icon.png")
    with ctx.monitor("dino"), ctx.start_app(["dino"]):
        time_remaining = 30
        # try to click Open Hardware Chat
        point, t = lib.locate_center_time(str(chat_icon), time_remaining)
        time_remaining -= t
        pyautogui.click(*point)
        # sit for the remaining time out of 30 seconds since navigating to chat
        time.sleep(time_remaining)
        ctx.screenshot("app.png")

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__), True)