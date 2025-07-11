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

from pathlib import Path
import importlib.resources as res
import inspect
from typing import Literal, Tuple
import subprocess
from subprocess import Popen
from signal import SIGINT, SIGABRT
from types import MethodType, TracebackType
from contextlib import AbstractContextManager
import sys
import os
from humanize import naturalsize
import argparse
import logging
import time

class ExperimentPath: # oh my god I'm so sick of getting paths wrong, types ftw
    def __init__(self, *pathsegments: str):
        self._inner = Path(*pathsegments)
    
    def joinpath(self, *pathsegments: str | Path):
        ret = ExperimentPath(str(self._inner))
        ret._inner = ret._inner.joinpath(*pathsegments)
        return ret

    def into_path(self, experiment: "Experiment") -> Path:
        return experiment.output_dir.joinpath(self._inner)

class PleaseNoMoreException(Exception):
    pass

class AlreadyRunningException(Exception):
    pass

def assert_not_running(regex: str) -> None:
    res = subprocess.run(["pgrep", regex])
    if res.returncode == 0:
        raise AlreadyRunningException(f"A process matching {regex} is already running")
    elif res.returncode == 1:
        return
    else:
        raise Exception(f"'pgrep {regex}' failed")



def get_resource(filename: str) -> Path:
    # https://stackoverflow.com/a/1095621/3882118
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    assert(module is not None)
    return res.as_file(res.files(module).joinpath(filename)).__enter__()

GEN_INFO = get_resource("gen-info.sh")
ADD_FILE = get_resource("add-file.sh")

def gen_info(out: Path) -> None:
    subprocess.run(["bash", str(GEN_INFO), str(out)])

def add_file(copy_to: Path, info_file: Path, *args: Path) -> None:
    subprocess.run(["bash", str(ADD_FILE)] + [ str(arg) for arg in args ] + [str(copy_to), str(info_file)])

chromium_reload_button = None
firefox_reload_button = None
def get_reload_button(browser: Literal["chromium", "firefox"]) -> Path:
    if browser == "chromium":
        global chromium_reload_button
        if chromium_reload_button is None:
            chromium_reload_button = get_resource("chromium_reload_button.png")
        return chromium_reload_button
    elif browser == "firefox":
        global firefox_reload_button
        if firefox_reload_button is None:
            firefox_reload_button = get_resource("firefox_reload_button.png")
        return firefox_reload_button
    
def reload_page(browser: Literal["chromium", "firefox"]) -> None:
    point = locate_center(get_reload_button(browser))
    assert point is not None
    pyautogui.click(*point)

def load_page(browser: Literal["chromium", "firefox"], url: str) -> None:
    if browser == "chromium":
        point = locate_center(get_reload_button("chromium"), timeout=10)
        assert point is not None
        (x, y) = point
        pyautogui.tripleClick(x=x+300, y=y)
    elif browser == "firefox":
        point = locate_center(get_reload_button("firefox"), timeout=10)
        (x, y) = point
        pyautogui.tripleClick(x=x+700, y=y)
    pyautogui.write(url)
    pyautogui.press('enter')

def start_monitor(regex: str, graph_out: Path, stdout_to_file: Path) -> Tuple[Popen[bytes], Path, Path]:
    with open(stdout_to_file, 'w') as f:
        popen = subprocess.Popen(["smaps-profiler", "-c", "-j", "-g", str(graph_out), "-m", regex], stdout=f)
        return (popen, graph_out, stdout_to_file)

def mem_str(mem: int | None) -> str:
    if mem is None:
        return "infinity"
    else:
        return str(mem)

def human_mem_str(mem: int | None) -> str:
    if mem is None:
        return "nolimit"
    else:
        return naturalsize(mem, True).replace(" ", "")

def start_with_mem(command: list[str], mem: int | None) -> Popen[bytes]:
    cmd = ["systemd-run", "--user", "--scope", "-p", "MemoryHigh={}".format(mem_str(mem))] + command
    return subprocess.Popen(cmd)

def parse_sysargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('output-directory')
    parser.add_argument('-i', '--info-filename', type=str, default=None)
    parser.add_argument('-m', '--memory-limit', type=int, default=None)
    return parser.parse_args(sys.argv)

def format_exception(e: BaseException) -> str:
    return "{}: {}".format(type(e).__name__, e)

def locate_center(image: str | Path, timeout: float = 0, confidence: float = 0.9) -> tuple[int, int]:
    point = pyautogui.locateCenterOnScreen(str(image), minSearchTime=timeout, confidence=confidence)
    assert point is not None
    return point

# work around for headless
try:
    import pyautogui
    def _screenshot(self: "Experiment", name: ExperimentPath = ExperimentPath("app.png")) -> None:
        path = self.path_of(name)
        pyautogui.screenshot(path)
        self.add_file(path)
except KeyError: # DISPLAY not defined
    def _screenshot(self: "Experiment", name: ExperimentPath = ExperimentPath("app.png")) -> None:
        pass

class Experiment(AbstractContextManager["Experiment", None]):
    def __init__(self, name: str, output_dir: Path, mem_limit: int | None, info_file: ExperimentPath | None = ExperimentPath("info.yaml"), log_file: ExperimentPath = ExperimentPath("log"), exit_exception_timeout: float = 20.0, exit_term_timeout: float = 30, exit_abrt_timeout: float = 40, leave_apps_open: bool = False):
        try:
            import pyautogui
            pyautogui.useImageNotFoundException(True)
        except KeyError: # DISPLAY not defined
            pass
        self.output_dir = output_dir
        os.makedirs(self.output_dir)
        if not info_file:
            info_file = ExperimentPath("info.yaml") 
        info_path = self.path_of(info_file)
        gen_info(info_path)
        self.info_path = info_path
        self.monitor_tuple: Tuple[Popen[bytes], Path, Path] | None = None
        self.screenshot = MethodType(_screenshot, self)
        self.mem_limit = mem_limit
        self.exit_exception_timeout = exit_exception_timeout
        self.exit_term_timeout = exit_term_timeout
        self.exit_abrt_timeout = exit_abrt_timeout
        self.leave_apps_open = leave_apps_open
        self.procs: list[Popen[bytes]] = []
        self.name = name
        self.logging_file = self.path_of(log_file)
        self.logger = logging.getLogger(self.name)
        # inspired by default format for Rust env_logger
        formatter = logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s")
        # https://stackoverflow.com/a/11582124/3882118
        fh = logging.FileHandler(self.logging_file)
        sh = logging.StreamHandler()
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(sh)
        self.logger.setLevel(logging.INFO)

    def path_of(self, path: ExperimentPath) -> Path:
        return path.into_path(self)

    @staticmethod
    def parse_sysargs() -> "Experiment":
        ns = parse_sysargs()
        return Experiment(ns.output_directory, ns.memory_limit, ns.info_filename)

    def add_file(self, *args: Path) -> None:
        add_file(self.output_dir, self.info_path, *args)

    # use this if you want Experiment context manager to automatically close app on exit or error
    def start(self, command: list[str]) -> Popen[bytes]:
        p = start_with_mem(command, self.mem_limit)
        self.procs.append(p)
        return p

    def stop(self, app: Popen[bytes], exception_timeout: float | None = 20.0, term_timeout: float | None = 30.0, abrt_timeout: float | None = 40.0) -> float:
        if app.poll() is not None:
            return 0
        self.logger.info("sending SIGTERM")
        app.terminate()
        start = time.time()
        duration = 0.0
        abrt_sent = False
        while True:
            duration = time.time() - start
            if app.poll() is not None:
                break
            elif (abrt_timeout is not None) and duration > abrt_timeout:
                self.screenshot("error_abort_timeout.png")
                self.logger.warning("sending SIGKILL")
                app.kill()
                break
            elif (term_timeout is not None) and duration > term_timeout and not abrt_sent:
                self.screenshot("error_terminate_timeout.png")
                self.logger.warning("sending SIGABRT")
                app.send_signal(SIGABRT)
                abrt_sent = True
        if (exception_timeout is not None) and duration > exception_timeout:
            raise PleaseNoMoreException
        return duration
            
    def start_monitor(self, regex: str, graph_file: ExperimentPath = ExperimentPath("graph.svg"), stdout_file: ExperimentPath = ExperimentPath("smaps_profiler.ndjson"), check_not_running: bool = True) -> None:
        if self.monitor_tuple:
            self.logger.warning("Experiment.start_monitor() called when Experiment.monitor_tuple was not None. Refusing to do anything.")
            return
        if check_not_running:
            assert_not_running(regex)
        graph = self.path_of(graph_file)
        stdout = self.path_of(stdout_file)
        self.monitor_tuple = start_monitor(regex, graph, stdout)

    def _stop_monitor(self) -> bool:
        if self.monitor_tuple:
            (popen, graph, stdout) = self.monitor_tuple
            popen.send_signal(SIGINT)
            popen.wait()
            self.add_file(graph, stdout)
            self.monitor_tuple = None
            return True
        else:
            return False

    def stop_monitor(self) -> None:
        if not self._stop_monitor():
            self.logger.warning("Experiment.stop_monitor() called when Experiment.monitor_tuple was falsy.")
    
    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> bool: # type: ignore[override]
        if exc_value is None:
            ret = True
        elif exc_type == KeyboardInterrupt:
            self.logger.info("keyboard-interrupted")
            ret = False
        else:
            self.screenshot("error_exception_raised.png")
            if any([ proc.poll() is not None for proc in self.procs ]):
                # some process terminated, assume out of memory,
                # which is expected.
                self.logger.warning("a process was found to be terminated, assuming out of memory")
                ret = True
            else:
                # all processes are still running, not out of memory,
                # so something's wrong with the script.
                self.logger.exception(exc_value)
                ret = False
        took_long_time = False
        if not self.leave_apps_open:
            for proc in self.procs:
                try:
                    self.stop(proc, self.exit_exception_timeout, self.exit_term_timeout, self.exit_abrt_timeout)
                except PleaseNoMoreException:
                    took_long_time = True
        self._stop_monitor()
        self.add_file(Path(self.logging_file))
        if took_long_time:
            raise PleaseNoMoreException
        return ret

