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

import pyperclip
from ..lib import Experiment, ExperimentPath, assert_not_running, human_mem_str, get_resource, locate_center, reload_page, start_with_mem
import sys
import os
from pathlib import Path

import pyautogui

class ExperimentParams:
    def __init__(self, name: str, command: list[str], mems: list[int | None]):
        self.name = name
        self.command = command
        self.mems = mems

URL = "https://browserbench.org/Speedometer3.1/"
EXPERIMENTS = [
    ExperimentParams("chromium", ["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", URL], [None]),
    ExperimentParams("firefox", ["firefox", "-P", "Experiments", URL], [None]),
]

def main() -> None:
    if len(sys.argv) != 2:
        print("Must specify output directory")
        sys.exit(1)

    for params in EXPERIMENTS:
        assert params.name == "chromium" or params.name == "firefox" 
        start_button = get_resource(f"start_button_{params.name}.png")
        details_button = get_resource(f"details_button_{params.name}.png")
        copy_json_button = get_resource(f"copy_json_button_{params.name}.png")
        for (i, mem) in enumerate(params.mems):
            mem_tag = "{:02d}_{}".format(i, human_mem_str(mem))
            output_dir = Path(sys.argv[1]).joinpath(params.name).joinpath(mem_tag)
            with Experiment(params.name, output_dir, mem) as ex:
                assert_not_running(params.name)
                start_with_mem(params.command, mem)
                for j in range(10):
                    try:
                        out = ExperimentPath(str(j))
                        os.makedirs(ex.path_of(out))
                        graph_file = out.joinpath("graph.svg")
                        json_file = out.joinpath("smaps-profiler.ndjson")
                        point = locate_center(start_button, timeout=10)

                        ex.start_monitor(params.name, graph_file=graph_file, stdout_file=json_file, check_not_running=False)

                        start = time.time()
                        pyautogui.click(*point)
                        point = locate_center(details_button, timeout=10*60)
                        end = time.time()

                        ex.stop_monitor()

                        pyautogui.click(*point)
                        point = locate_center(copy_json_button, timeout=10)
                        pyautogui.click(*point)
                        bench_json = ex.path_of(out.joinpath("benchmark.json"))
                        with open(bench_json, 'w') as f:
                            f.write(pyperclip.paste())
                        time_file = ex.path_of(out.joinpath("time_ms"))
                        with open(time_file, 'w') as f:
                            f.write(str((end - start) * 1000))
                        reload_page(params.name)
                    except Exception as e:
                        ex.logger().exception(e)
