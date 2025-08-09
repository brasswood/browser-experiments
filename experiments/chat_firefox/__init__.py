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
import subprocess

def get_version() -> str:
    return str(subprocess.run(["firefox", "--version"], capture_output=True).stdout)

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    init_page = "about:blank" if do_baseline else "mov.im/chat"
    chat_button = lib.get_resource("open_hw_chat_button.png")
    with ctx.monitor("firefox"), ctx.start_app(["firefox", "-P", "Experiments", init_page]):
        if do_baseline:
            # wait 30 on the blank page
            time.sleep(30)
            ctx.screenshot("blank.png")
            # navigate to mov.im/chat
            lib.load_page("firefox", 'mov.im/chat')
        time_remaining = 30
        # try to click Open Hardware Chat
        point, t = lib.locate_center_time(chat_button, time_remaining)
        time_remaining -= t
        pyautogui.click(*point)
        # sit for the remaining time out of 30 seconds since navigating to chat
        time.sleep(time_remaining)
        ctx.screenshot("app.png")

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__), True)
