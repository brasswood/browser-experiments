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
from ..lib import Context, MEGABYTE, TookLongTimeException
from .. import lib
import pyautogui
from pyautogui import ImageNotFoundException

class ExperimentParams:
    def __init__(self, name: str, command: list[str], mems: list[int | None]):
        self.name = name
        self.command = command
        self.mems = mems

URL = "https://browserbench.org/Speedometer3.1/"

RATE = 0.8
N = 17
# N = 1
SAMPLES = 10
# SAMPLES = 1

EXPERIMENTS = [
    ExperimentParams("chromium", ["chromium-browser", "--hide-crash-restore-bubble", "--no-sandbox", URL], lib.decay(910 * MEGABYTE, RATE, N)),
    ExperimentParams("firefox", ["firefox", "-P", "Experiments", URL], lib.decay(1380 * MEGABYTE, RATE, N)),
]

def main() -> None:
    with Context.from_module(__name__) as top_ctx, top_ctx.get_child("out") as out_ctx:
        for params in EXPERIMENTS:
            assert params.name == "chromium" or params.name == "firefox"
            start_button = lib.get_resource(f"start_button_{params.name}.png")
            details_button = lib.get_resource(f"details_button_{params.name}.png")
            copy_json_button = lib.get_resource(f"copy_json_button_{params.name}.png")
            with out_ctx.get_child(params.name) as browser_ctx:
                for (i, mem) in enumerate(params.mems):
                    with browser_ctx.get_child_with_mem(i, mem) as mem_ctx:
                        try:
                            lib.assert_not_running(params.name)
                            with mem_ctx.start_app(params.command):
                                for j in range(SAMPLES):
                                    with mem_ctx.get_child_with_sample(j) as sample_ctx:
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
                                            sample_ctx.logger.error("Image not found, perhaps the application is too unresponsive. Refusing to reduce memory any more for this workload.", exc_info=True)
                                            raise
                                        except Exception as e:
                                            sample_ctx.logger.exception(e)
                        except TookLongTimeException as e:
                            mem_ctx.logger.warning(f"Application took longer than {e.warn_time} seconds to exit. Refusing to reduce memory any more for this workload.")
                            break
                        except ImageNotFoundException:
                            # same as ImageNotFoundException above; we may be thrashing so just end the experimentation here
                            break
                        except Exception as e:
                            mem_ctx.logger.exception(e)
