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

import shutil
import time
import pyperclip
from ..lib import Context, MEGABYTE, TookLongTimeException, RelPath
from .. import lib
import pyautogui
from pyautogui import ImageNotFoundException

class ExperimentParams:
    def __init__(self, name: str, command: list[str], mems: list[int | None]):
        self.name = name
        self.command = command
        self.mems = mems

URL = "https://browserbench.org/Speedometer3.1/"

RATE = 0.7
N = 12
# N = 1
SAMPLES = 10
# SAMPLES = 1

EXPERIMENTS = [
    ExperimentParams("chromium", ["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", URL], lib.decay(910 * MEGABYTE, RATE, N)),
    ExperimentParams("firefox", ["firefox", "-P", "Experiments", URL], lib.decay(1380 * MEGABYTE, RATE, N)),
]

def main() -> None:
    top_ctx = Context.from_module(__name__)
    graphs_all = top_ctx.joinpath("graphs_all")
    lib.ensure_dir_exists(graphs_all)
    for params in EXPERIMENTS:
        assert params.name == "chromium" or params.name == "firefox"
        start_button = lib.get_resource(f"start_button_{params.name}.png")
        details_button = lib.get_resource(f"details_button_{params.name}.png")
        copy_json_button = lib.get_resource(f"copy_json_button_{params.name}.png")
        browser_ctx = top_ctx.get_child(params.name)
        for (i, mem) in enumerate(params.mems):
            mem_ctx = browser_ctx.get_child_with_mem(i, mem)
            try:
                lib.assert_not_running(params.name)
                with mem_ctx.start_app(params.command):
                    for j in range(SAMPLES):
                        sample_ctx = mem_ctx.get_child_with_sample(j)
                        try:
                            point = lib.locate_center(start_button, timeout=10)
                            with sample_ctx.monitor(params.name, check_if_running=False):
                                start = time.time()
                                pyautogui.click(*point)
                                point = lib.locate_center(details_button, timeout=10*60)
                                end = time.time()
                            pyautogui.click(*point)
                            point = lib.locate_center(copy_json_button, timeout=10)
                            pyautogui.click(*point)
                            with sample_ctx.open("benchmark.json", 'w') as f:
                                f.write(pyperclip.paste())
                            with sample_ctx.open("python_time_ms", 'w') as f:
                                f.write(str((end - start) * 1000))
                            lib.reload_page(params.name)
                        except ImageNotFoundException:
                            # in this case, we just break to close the browser, because we
                            # are ordinarily leaving the browser open between runs so we're hopeless
                            # to get an accurate next measurement without waiting arbitrarily long.
                            sample_ctx.logger.error("Image not found, perhaps the application is too unresponsive. Copying graph to graphs_all anyway.", exc_info=True)
                            break
                        except Exception as e:
                            sample_ctx.logger.exception(e)
                            continue
                        finally:
                            shutil.copy2(sample_ctx.joinpath("graph.svg"), graphs_all.joinpath(f"{browser_ctx.name}_{mem_ctx.name}_{sample_ctx.name}.svg"))
            except TookLongTimeException:
                mem_ctx.logger.warning("Application took longer than 25 seconds to exit. Refusing to reduce memory any more for this workload.")
                break
            except Exception as e:
                mem_ctx.logger.exception(e)
                continue
