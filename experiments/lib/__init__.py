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
import shutil
from typing import IO, Any, Literal, Self
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
from pathspec import PathSpec
import pyautogui


def project_root() -> Path:
    return Path(__file__).parent.parent.parent

# ChatGPT gave me this wonderful function which I then heavily modified
def copy_project(output_dir: Path) -> None:
    os.makedirs(output_dir)
    root = project_root()
    with open(root/".gitignore", 'r') as f:
        spec = PathSpec.from_lines("gitwildmatch", f)
    for match in spec.match_tree_entries(root, negate=True):
        if match.is_dir():
            os.makedirs(output_dir/match.path)
        else:
            shutil.copy2(root/match.path, output_dir/match.path)

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
    # reload button stuck highlighted in chromium.
    # pyautogui.moveRel(10, 10)
    # pyautogui.moveRel(-10, -10)

def load_page(browser: Literal["chromium", "firefox"], url: str) -> None:
    if browser == "chromium":
        point = locate_center(get_reload_button("chromium"), timeout=10)
        assert point is not None
        (x, y) = point
        pyautogui.tripleClick(x=x+700, y=y)
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

KIBIBYTE: int = 1024
MEBIBYTE: int = KIBIBYTE * 1024
GIBIBYTE: int = MEBIBYTE * 1024

KILOBYTE: int = 1000
MEGABYTE: int = KILOBYTE * 1000
GIGABYTE: int = MEGABYTE * 1000

def decay(start: int, rate: float, n: int) -> list[int | None]:
    ret: list[int | None] = [None]
    mem = start
    for _ in range(n+1): # want to include None, start, all the way up to start * rate**n
        ret.append(mem)
        mem = int(mem*rate)
    return ret

def command_with_mem(command: list[str], mem: int | None) -> list[str]:
    return ["systemd-run", "--user", "--scope", "-p", "MemoryHigh={}".format(mem_str(mem))] + command

def parse_sysargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('output-directory')
    parser.add_argument('-m', '--memory-limit', type=int, default=None)
    return parser.parse_args(sys.argv)

def format_exception(e: BaseException) -> str:
    return "{}: {}".format(type(e).__name__, e)

def locate_center(image: str | Path, timeout: float = 0, confidence: float = 0.9) -> tuple[int, int]:
    point = pyautogui.locateCenterOnScreen(str(image), minSearchTime=timeout, confidence=confidence)
    assert point is not None
    return point

def get_logger(name: str, file: Path) -> Logger:
    logger = logging.getLogger(name)
    # inspired by default format for Rust env_logger
    formatter = logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s")
    # https://stackoverflow.com/a/11582124/3882118
    fh = logging.FileHandler(file)
    sh = logging.StreamHandler()
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.INFO)
    return logger

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

    def into_path(self: Self, context: "Context") -> Path:
        return context.dir().joinpath(self._inner)

class Context(AbstractContextManager["Context", bool]):
    @classmethod
    def to_context_path(cls, path: ContextPath | str) -> ContextPath:
        if isinstance(path, str):
            return ContextPath(path)
        else:
            return path

    def path_of(self, path: ContextPath) -> Path:
        return path.into_path(self)

    @abstractmethod
    def name(self) -> str:
        pass

    def open(self, path: ContextPath, mode: str) -> IO[Any]:
        p = self.path_of(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return open(p, mode)

    @abstractmethod
    def exit_timeouts(self) -> ExitTimeouts:
        pass

    @abstractmethod
    def parent(self) -> "Context | None":
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
    def monitor(self) -> Popen[bytes] | None:
        pass

    @abstractmethod
    def set_monitor(self, monitor: Popen[bytes] | None) -> None:
        pass

    @abstractmethod
    def procs(self) -> list[Popen[bytes]]:
        pass

    @abstractmethod
    def _start_command(self, command: list[str]) -> list[str]:
        pass

    def start(self, command: list[str]) -> Popen[bytes]:
        ret = Popen(self._start_command(command))
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
            
    def start_monitor(self, regex: str, graph_file: ContextPath | str = "graph.svg", stdout_file: ContextPath | str = "smaps_profiler.ndjson", check_not_running: bool = True) -> None:
        if self.monitor():
            self.logger().warning("Experiment.start_monitor() called when Experiment.monitor_tuple was not None. Refusing to do anything.")
            return
        if check_not_running:
            assert_not_running(regex)
        graph = self.path_of(self.to_context_path(graph_file))
        stdout = self.path_of(self.to_context_path(stdout_file))
        self.set_monitor(start_monitor(regex, graph, stdout))

    def _stop_monitor(self) -> bool:
        m = self.monitor()
        if m:
            m.send_signal(SIGINT)
            m.wait()
            self.set_monitor(None)
            return True
        else:
            return False

    def stop_monitor(self) -> None:
        if not self._stop_monitor():
            self.logger().warning("Experiment.stop_monitor() called when Experiment.monitor was falsy.")

    def screenshot(self, name: ContextPath | str = "app.png") -> None:
        path = self.path_of(self.to_context_path(name))
        pyautogui.screenshot(path)
    
    def reload_page(self, browser: Literal["chromium", "firefox"]) -> None:
        reload_page(browser)

    def load_page(self, browser: Literal["chromium", "firefox"], url: str) -> None:
        load_page(browser, url)

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

class Experiment(Context):
    def __init__(self, name: str, output_dir: Path, exit_timeouts: ExitTimeouts = ExitTimeouts(20, 30, 40)):
        pyautogui.useImageNotFoundException(True)
        self.output_dir = output_dir
        self.m_name = name
        self.m_logger = None
        os.makedirs(self.dir())
        info_path = self.path_of(ContextPath("info.yaml"))
        gen_info(info_path)
        with self.open(ContextPath("sys_argv"), 'w') as f:
            f.write(" ".join(sys.argv))
        # ChatGPT helped
        cmdline = open(f"/proc/self/cmdline", 'r').read().split('\0')
        cmdline = " ".join([c for c in cmdline])
        with self.open(ContextPath("cmdline"), 'w') as f:
            f.write(f"{os.getcwd()}$ ")
            f.write(cmdline)
        copy_project(self.path_of(ContextPath("src")))
        self.m_monitor: Popen[bytes] | None = None
        self.m_exit_timeouts = exit_timeouts
        self.procs_list: list[Popen[bytes]] = []
        
    @staticmethod
    def parse_sysargs() -> "Experiment":
        ns = parse_sysargs()
        return Experiment("temporary name should be caller module", ns.output_directory)

    """
    use this if you want Experiment context manager to automatically close app on exit or error
    """
    def _start_command(self, command: list[str]) -> list[str]:
        return command

    def exit_timeouts(self) -> ExitTimeouts:
        return self.m_exit_timeouts

    def parent(self) -> Context | None:
        return None

    def rel_base_dir(self) -> Path:
        return self.output_dir

    def logger(self) -> Logger:
        if self.m_logger is None:
            self.m_logger = get_logger(self.m_name, self.path_of(ContextPath("log.txt")))
        return self.m_logger

    def monitor(self) -> Popen[bytes] | None:
        return self.m_monitor

    def set_monitor(self, monitor: Popen[bytes] | None) -> None:
        self.m_monitor = monitor

    def procs(self) -> list[Popen[bytes]]:
        return self.procs_list

    def name(self) -> str:
        return self.m_name

class Memory(Context):
    def __init__(self, parent: Context, idx: int, mem: int | None):
        self.m_parent = parent
        self.mem = mem
        self.m_name = f"{idx:02d}_{human_mem_str(mem)}"
        self.base_dir = Path(self.m_name)
        self.m_logger = None
        os.makedirs(self.dir())
        self.m_procs: list[Popen[bytes]] = []
        self.m_monitor = None

    def name(self) -> str:
        return self.m_name

    def exit_timeouts(self) -> ExitTimeouts:
        return self.m_parent.exit_timeouts()

    def parent(self) -> Context | None:
        return self.m_parent

    def rel_base_dir(self) -> Path:
        return self.base_dir

    def logger(self) -> Logger:
        if self.m_logger is None:
            self.m_logger = get_logger(f"{self.m_parent.name()}_{self.m_name}", self.path_of(ContextPath("log.txt")))
        return self.m_logger

    def monitor(self) -> Popen[bytes] | None:
        return self.m_monitor

    def set_monitor(self, monitor: Popen[bytes] | None) -> None:
        self.m_monitor = monitor

    def procs(self) -> list[Popen[bytes]]:
        return self.m_procs

    def _start_command(self, command: list[str]) -> list[str]:
        return command_with_mem(command, self.mem)

class Sub(Context):
    def __init__(self, parent: Context, name: str):
        self.m_parent = parent
        self.m_name = name
        self.base_dir = Path(self.m_name)
        self.m_logger = None
        os.makedirs(self.dir())
        self.m_procs: list[Popen[bytes]] = []
        self.m_monitor = None

    def name(self) -> str:
        return self.m_name

    def exit_timeouts(self) -> ExitTimeouts:
        return self.m_parent.exit_timeouts()

    def parent(self) -> Context | None:
        return self.m_parent

    def rel_base_dir(self) -> Path:
        return self.base_dir

    def logger(self) -> Logger:
        if self.m_logger is None:
            self.m_logger = get_logger(f"{self.m_parent.name()}_{self.m_name}", self.path_of(ContextPath("log.txt")))
        return self.m_logger

    def monitor(self) -> Popen[bytes] | None:
        return self.m_monitor

    def set_monitor(self, monitor: Popen[bytes] | None) -> None:
        self.m_monitor = monitor

    def procs(self) -> list[Popen[bytes]]:
        return self.m_procs

    def _start_command(self, command: list[str]) -> list[str]:
        return command