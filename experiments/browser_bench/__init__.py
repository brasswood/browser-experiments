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

import os
import shutil
import time

import pyperclip
from ..lib import MEGABYTE, ContextPath, Experiment, Memory, Sub, TookLongTimeException, assert_not_running, get_resource, locate_center, reload_page, decay
import sys
from pathlib import Path

import pyautogui

class ExperimentParams:
    def __init__(self, name: str, command: list[str], mems: list[int | None]):
        self.name = name
        self.command = command
        self.mems = mems

URL = "https://browserbench.org/Speedometer3.1/"

RATE = 0.7
N = 10

EXPERIMENTS = [
    ExperimentParams("chromium", ["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", URL], decay(910 * MEGABYTE, RATE, N)),
    ExperimentParams("firefox", ["firefox", "-P", "Experiments", URL], decay(1380 * MEGABYTE, RATE, N)),
]

def main() -> None:
    if len(sys.argv) != 2:
        print("Must specify output directory")
        sys.exit(1)

    with Experiment("browser_bench", Path(sys.argv[1])) as ex:
        graphs_all = ex.path_of(ContextPath("graphs_all"))
        os.makedirs(graphs_all)
        for params in EXPERIMENTS:
            assert params.name == "chromium" or params.name == "firefox"
            start_button = get_resource(f"start_button_{params.name}.png")
            details_button = get_resource(f"details_button_{params.name}.png")
            copy_json_button = get_resource(f"copy_json_button_{params.name}.png")
            with Sub(ex, params.name) as sub:
                for (i, mem) in enumerate(params.mems):
                    assert_not_running(params.name)
                    with Memory(sub, i, mem) as mem_ex:
                        mem_ex.start(params.command)
                        took_long_time = False
                        for j in range(10):
                            with Sub(mem_ex, f"{j:02d}") as sample_ex:
                                try:
                                    point = locate_center(start_button, timeout=10)

                                    sample_ex.start_monitor(params.name, check_not_running=False)

                                    start = time.time()
                                    pyautogui.click(*point)
                                    point = locate_center(details_button, timeout=10*60)
                                    end = time.time()

                                    sample_ex.stop_monitor()

                                    pyautogui.click(*point)
                                    point = locate_center(copy_json_button, timeout=10)
                                    pyautogui.click(*point)
                                    with sample_ex.open(ContextPath("benchmark.json"), 'w') as f:
                                        f.write(pyperclip.paste())
                                    with sample_ex.open(ContextPath("time_ms"), 'w') as f:
                                        f.write(str((end - start) * 1000))
                                except TookLongTimeException:
                                    sample_ex.logger().warning("Application took longer than 25 seconds to exit. Refusing to reduce memory any more for this workload.")
                                    took_long_time = True
                                except Exception:
                                    pass
                                shutil.copy2(sample_ex.path_of(ContextPath("graph.svg")), graphs_all.joinpath(f"{sub.name()}_{mem_ex.name()}_{sample_ex.name()}.svg"))
                            try:
                                reload_page(params.name)
                            except Exception:
                                break
                        if took_long_time:
                            break
