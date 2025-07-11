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

from abc import abstractmethod
import copy
import logging
from pathlib import Path
import importlib.resources as res
import inspect
from typing import Literal, Self
import subprocess
from subprocess import Popen
from signal import SIGINT, SIGABRT
from types import TracebackType
from contextlib import AbstractContextManager
import sys
import os
from humanize import naturalsize
import argparse
from logging import Logger
import time
import pyautogui



class TookLongTimeException(Exception):
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

def gen_info(out: Path) -> None:
    subprocess.run(["bash", str(GEN_INFO), str(out)])

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

def start_monitor(regex: str, graph_out: Path, stdout_to_file: Path) -> Popen[bytes]:
    with open(stdout_to_file, 'w') as f:
        popen = subprocess.Popen(["smaps-profiler", "-c", "-j", "-g", str(graph_out), "-m", regex], stdout=f)
        return popen

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

class ExitTimeouts:
    def __init__(self, warn: float, term: float, abrt: float):
        self.warn = warn
        self.term = term
        self.abrt = abrt

class ContextPath:
    def __init__(self, *pathsegments: str):
        self._inner = Path(*pathsegments)
    
    def joinpath(self: Self, *pathsegments: str | Path) -> Self:
        ret = copy.deepcopy(self)
        ret._inner = ret._inner.joinpath(*pathsegments)
        return ret

    def into_path(self: Self, context: "Context[Self]") -> Path:
        return context.dir().joinpath(self._inner)

class Context[CP: ContextPath](AbstractContextManager["Context", bool]):
    @classmethod
    @abstractmethod
    def path_t(cls) -> type[CP]:
        pass

    @classmethod
    def to_path_t(cls, path: CP | str) -> CP:
        if isinstance(path, str):
            return cls.path_t()(path)
        else:
            return path

    def path_of(self, path: CP) -> Path:
        return path.into_path(self)

    @abstractmethod
    def exit_timeouts(self) -> ExitTimeouts:
        pass

    @abstractmethod
    def parent(self) -> "Context[ContextPath] | None":
        pass

    @abstractmethod
    def rel_base_dir(self) -> Path:
        pass

    def dir(self) -> Path:
        parent = self.parent()
        if parent is None:
            return self.rel_base_dir()
        else:
            return parent.dir().joinpath(self.rel_base_dir())

    @abstractmethod
    def logger(self) -> Logger:
        pass

    @abstractmethod
    def procs(self) -> list[Popen[bytes]]:
        pass

    @abstractmethod
    def _start(self, command: list[str]) -> Popen[bytes]:
        pass

    def start(self, command: list[str]) -> Popen[bytes]:
        ret = self._start(command)
        self.procs().append(ret)
        return ret

    def stop(self, app: Popen[bytes], term_timeout: float | None = 30.0, abrt_timeout: float | None = 40.0) -> float:
        if app.poll() is not None:
            return 0
        self.logger().info("sending SIGTERM")
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
                self.logger().warning("sending SIGKILL")
                app.kill()
                break
            elif (term_timeout is not None) and duration > term_timeout and not abrt_sent:
                self.screenshot("error_terminate_timeout.png")
                self.logger().warning("sending SIGABRT")
                app.send_signal(SIGABRT)
                abrt_sent = True
        return duration
            
    def start_monitor(self, regex: str, graph_file: CP | str = "graph.svg", stdout_file: CP | str = "smaps_profiler.ndjson", check_not_running: bool = True) -> None:
        if self.monitor:
            self.logger().warning("Experiment.start_monitor() called when Experiment.monitor_tuple was not None. Refusing to do anything.")
            return
        if check_not_running:
            assert_not_running(regex)
        graph = self.path_of(self.to_path_t(graph_file))
        stdout = self.path_of(self.to_path_t(stdout_file))
        self.monitor = start_monitor(regex, graph, stdout)

    def _stop_monitor(self) -> bool:
        if self.monitor:
            self.monitor.send_signal(SIGINT)
            self.monitor.wait()
            self.monitor = None
            return True
        else:
            return False

    def stop_monitor(self) -> None:
        if not self._stop_monitor():
            self.logger().warning("Experiment.stop_monitor() called when Experiment.monitor_tuple was falsy.")

    def screenshot(self, name: CP | str = "app.png") -> None:
        path = self.path_of(self.to_path_t(name))
        pyautogui.screenshot(path)

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> bool:
        if exc_value is None:
            ret = True
        elif exc_type == KeyboardInterrupt:
            self.logger().info("keyboard-interrupted")
            ret = False
        else:
            self.screenshot("error_exception_raised.png")
            if any([ proc.poll() is not None for proc in self.procs() ]):
                # some process terminated, assume out of memory,
                # which is expected.
                self.logger().warning("a process was found to be terminated, assuming out of memory")
                ret = True
            else:
                # all processes are still running, not out of memory,
                # so something's wrong with the script.
                self.logger().exception(exc_value)
                ret = False
        took_long_time = False
        for proc in self.procs():
            timeouts = self.exit_timeouts()
            if self.stop(proc, timeouts.term, timeouts.abrt) > timeouts.warn:
                took_long_time = True
        self._stop_monitor()
        if took_long_time:
            raise TookLongTimeException
        return ret

class ExperimentPath(ContextPath): # oh my god I'm so sick of getting paths wrong, types ftw
    pass
    
class Experiment(Context[ExperimentPath]):
    def __init__(self, name: str, output_dir: Path, mem_limit: int | None, info_file: ExperimentPath | None = ExperimentPath("info.yaml"), log_file: ExperimentPath = ExperimentPath("log"), exit_timeouts: ExitTimeouts = ExitTimeouts(20, 30, 40)):
        pyautogui.useImageNotFoundException(True)
        self.output_dir = output_dir
        os.makedirs(self.output_dir)
        if not info_file:
            info_file = ExperimentPath("info.yaml") 
        info_path = self.path_of(info_file)
        gen_info(info_path)
        self.info_path = info_path
        self.monitor: Popen[bytes] | None = None
        self.mem_limit = mem_limit
        self.m_exit_timeouts = exit_timeouts
        self.procs_list: list[Popen[bytes]] = []
        self.name = name
        self.logging_file = self.path_of(log_file)
        self.m_logger = logging.getLogger(self.name)
        # inspired by default format for Rust env_logger
        formatter = logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s")
        # https://stackoverflow.com/a/11582124/3882118
        fh = logging.FileHandler(self.logging_file)
        sh = logging.StreamHandler()
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)
        self.m_logger.addHandler(fh)
        self.m_logger.addHandler(sh)
        self.m_logger.setLevel(logging.INFO)

    def path_of(self, path: ExperimentPath) -> Path:
        return path.into_path(self)

    @staticmethod
    def parse_sysargs() -> "Experiment":
        ns = parse_sysargs()
        return Experiment(ns.output_directory, ns.memory_limit, ns.info_filename)

    # use this if you want Experiment context manager to automatically close app on exit or error
    def _start(self, command: list[str]) -> Popen[bytes]:
        p = start_with_mem(command, self.mem_limit)
        self.procs_list.append(p)
        return p

    @classmethod
    def path_t(cls) -> type[ExperimentPath]:
        return ExperimentPath

    def exit_timeouts(self) -> ExitTimeouts:
        return self.m_exit_timeouts

    def parent(self) -> Context[ContextPath] | None:
        return None

    def rel_base_dir(self) -> Path:
        return self.output_dir

    def logger(self) -> Logger:
        return self.m_logger

    def procs(self) -> list[Popen[bytes]]:
        return self.procs_list

