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


from logging import Logger
import os
from pathlib import Path
import shutil
from subprocess import Popen
from typing import Literal
from .lib import Context, ContextPath, ExitTimeouts, Experiment, Memory, Sub, TookLongTimeException
import sys
from . import ALL_MEM


"""
Has an inner Sub. Monitor belongs to the Sub. Ability to start application belongs to this. Application itself belongs to parent.
"""
class FunkyContext(Context):
    def __init__(self, parent: Context, range: int, browser: Literal["chromium", "firefox"]):
        self.m_parent = parent
        self.range = range
        self.browser = browser

    def set_count(self, count: int) -> None:
        self.count = count
        self._inner = Sub(self.m_parent, f"{self.count:02d}")
    
    def _start_command(self, command: list[str]) -> list[str]:
        return []
    
    def start(self, command: list[str]) -> Popen[bytes]:
        if self.count == 0:
            return self.m_parent.start(command)
        else:
            assert self.browser == "chromium" or self.browser == "firefox"
            self.load_page(self.browser, "about:blank")
        return self.m_parent.procs()[0]

    def stop(self, app: Popen[bytes], term_timeout: float | None = 30.0, abrt_timeout: float | None = 40.0) -> float:
        if self.count == self.range - 1:
            return self.m_parent.stop(app, term_timeout, abrt_timeout)
        return 0.0

    def start_monitor(self, regex: str, graph_file: ContextPath | str = "graph.svg", stdout_file: ContextPath | str = "smaps-profiler.ndjson", check_not_running: bool = True) -> None:
        check = self.count == 0
        self._inner.start_monitor(regex, graph_file, stdout_file, check)

    def _stop_monitor(self) -> bool:
        return self._inner._stop_monitor()

    def name(self) -> str:
        return self._inner.name()

    def exit_timeouts(self) -> ExitTimeouts:
        return self.m_parent.exit_timeouts()

    def rel_base_dir(self) -> Path:
        return self._inner.rel_base_dir()
    
    def parent(self) -> Context:
        return self.m_parent

    def logger(self) -> Logger:
        return self._inner.logger()
    
    def monitor(self) -> Popen[bytes] | None:
        return self._inner.monitor()
    
    def set_monitor(self, monitor: Popen[bytes] | None) -> None:
        self._inner.set_monitor(monitor)

    def procs(self) -> list[Popen[bytes]]:
        return self.m_parent.procs()
    
    def screenshot(self, name: ContextPath | str = "app.png") -> None:
        self._inner.screenshot(name)

def parse_sysargs() -> Path:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_directory>")
        sys.exit(1)
    return Path(sys.argv[1])

def took_long_time_warning(ex: Context) -> None:
    ex.logger().warning("Application took longer than 25 seconds to exit. Refusing to reduce memory any more for this workload.")

def main() -> None:
    with Experiment("classic-with-samples", parse_sysargs()) as ex:
        all_graphs_dir = ContextPath("graphs_all")
        os.makedirs(ex.path_of(all_graphs_dir))
        for params in ALL_MEM:
            with Sub(ex, params.name()) as sub_ex:
                for (i, mem) in enumerate(params.mems):
                    with Memory(sub_ex, i, mem) as mem_ex:
                        took_long_time = False
                        if "web" in params.name():
                            browser = "chromium"
                        elif "firefox" in params.name():
                            browser = "firefox"
                        else:
                            for j in range(10):
                                try:
                                    with Sub(mem_ex, f"{j:02d}") as last_ex:
                                        try:
                                            params.module.run_experiment(last_ex)
                                        except Exception as e:
                                            last_ex.logger().exception(e)
                                        last_ex.stop_monitor()
                                        path_2 = f"{sub_ex.name()}_{mem_ex.name()}_{last_ex.name()}.svg"
                                        shutil.copy2(last_ex.path_of(ContextPath("graph.svg")), ex.path_of(all_graphs_dir)/path_2)
                                except TookLongTimeException:
                                    took_long_time_warning(last_ex)
                                    took_long_time = True
                            if took_long_time:
                                break
                                continue

                        with FunkyContext(mem_ex, 10, browser) as funky_ex:
                            assert isinstance(funky_ex, FunkyContext)
                            for j in range(10):
                                try:
                                    funky_ex.set_count(j)
                                    params.module.run_experiment(funky_ex)
                                except TookLongTimeException:
                                    took_long_time_warning(funky_ex)
                                    took_long_time = True
                                except Exception:
                                    pass
                                funky_ex.stop_monitor()
                                path_2 = f"{sub_ex.name()}_{funky_ex.name()}_{mem_ex.name()}.svg"
                                shutil.copy2(funky_ex.path_of(ContextPath("graph.svg")), ex.path_of(all_graphs_dir)/path_2)
                            if took_long_time:
                                break
if __name__ == "__main__":
    main()