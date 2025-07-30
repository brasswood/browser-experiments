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
from ..lib import App, Context
from .. import lib
import subprocess
import signal
import pyautogui

def die_evolution_die():
    # Well this sucks
    subprocess.run(["systemctl", "--user", "stop", "evolution-addressbook-factory.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-calendar-factory.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-source-registry.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-user-prompter.service"])
    subprocess.run(["pkill", "-f", "evolution-alarm-notify"])

def custom_term(app: App):
    app.send_signal(signal.SIGTERM, 'main') # terminate main process
    app.send_signal(signal.SIGTERM, 'all') # terminate all processes (evolution is so stubborn)
    die_evolution_die()

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    folder_options = (lib.get_resource("experiment_folder.png"), lib.get_resource("experiment_folder_highlighted.png"))
    header = lib.get_resource("folder_header.png")
    with ctx.monitor("evolution"), ctx.start_app(["evolution"], custom_term_routine=custom_term):
        # Run experiment
        time_remaining = 30

        point, t = lib.locate_center_time(folder_options, time_remaining)
        time_remaining -= t
        pyautogui.click(*point)
        
        (x, y), t = lib.locate_center_time(header, time_remaining)
        time_remaining -= t
        pyautogui.moveTo(x, y+20)
        pyautogui.click(x, y+20)

        time.sleep(time_remaining)
        ctx.screenshot("app.png")

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__), True)

if __name__ == "__main__":
    main()
