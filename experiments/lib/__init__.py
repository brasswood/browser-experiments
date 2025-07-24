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

import logging
from pathlib import Path
import importlib.resources as res
import inspect
import shutil
from typing import IO, Any, Literal, Self
import subprocess
from subprocess import Popen
from signal import SIGINT, SIGTERM, SIGABRT, SIGKILL
from types import ModuleType, TracebackType
from contextlib import AbstractContextManager
import sys
import os
from humanize import naturalsize
import argparse
from logging import Logger
import time
from pathspec import PathSpec
import pyautogui
import uuid

pyautogui.useImageNotFoundException(True)

class RelPath(Path):
    pass

def project_root() -> Path:
    return Path(__file__).parent.parent.parent

# ChatGPT gave me this wonderful function which I then heavily modified
def copy_project(output_dir: Path) -> None:
    os.makedirs(output_dir)
    root = project_root()
    with open2(root/".gitignore", 'r') as f:
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
    
def get_module(stack_distance: int = 0) -> ModuleType:
    # https://stackoverflow.com/a/1095621/3882118
    frame = inspect.stack()[1 + stack_distance]
    module = inspect.getmodule(frame[0])
    assert(module is not None)
    return module

def get_resource(filename: str) -> Path:
    module = get_module(1)
    return res.as_file(res.files(module).joinpath(filename)).__enter__()

GEN_INFO = get_resource("gen-info.sh")

def gen_info(out: Path) -> None:
    ensure_dir_exists(out.parent)
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

def start_monitor(regex: str, graph_out: Path, stdout_to_file: Path, check_if_running: bool = True) -> Popen[bytes]:
    if check_if_running:
        assert_not_running(regex)
    with open2(stdout_to_file, 'w') as f:
        popen = subprocess.Popen([project_root() / "smaps-profiler/target/release/smaps-profiler", "-c", "-j", "-g", str(graph_out), "-m", regex], stdout=f)
        return popen

def systemd_mem_str(mem: int | None) -> str:
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
    """
    start: the first memory constraint
    rate: rate to decay the memory constraint each iteration (fraction)
    n: number of iterations to perform (first iteration will always be unconstrained)
    """
    ret: list[int | None] = []
    if n > 0:
        ret.append(None)
        mem = start
        for _ in range(n-1): # want to include None, start, all the way up to start * rate**n
            ret.append(mem)
            mem = int(mem*rate)
    return ret

def start_with_mem(command: list[str], mem: int | None) -> Popen[bytes]:
    return Popen(["systemd-run", "--user", "--scope", "--unit=browser_experiment", "--collect", "-p", "MemoryHigh={}".format(systemd_mem_str(mem))] + command)

class Args:
    def __init__(self, output_dir: Path, mem: int | None):
        self.output_dir = output_dir
        self.mem = mem

# ChatGPT goated
def get_prog():
    main_module = sys.modules["__main__"]
    package = getattr(main_module, "__package__", None)
    if package:
        return f"python -m {package}"
    else:
        return sys.argv[0]


def parse_sysargs_with_mem() -> Args:
    parser = argparse.ArgumentParser(prog=get_prog())
    parser.add_argument('output_directory', metavar="output-directory")
    parser.add_argument('-m', '--memory-limit', type=int, default=None)
    ns = parser.parse_args()
    return Args(ns.output_directory, ns.memory_limit)

def parse_sysargs() -> Path:
    parser = argparse.ArgumentParser(prog=get_prog())
    parser.add_argument('output_directory', metavar='output-directory')
    ns = parser.parse_args()
    return Path(ns.output_directory)

def format_exception(e: BaseException) -> str:
    return "{}: {}".format(type(e).__name__, e)

def locate_center(image: str | Path, timeout: float = 0, confidence: float = 0.9) -> tuple[int, int]:
    point = pyautogui.locateCenterOnScreen(str(image), minSearchTime=timeout, confidence=confidence)
    assert point is not None
    return point

def ensure_dir_exists(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def get_logger(name: str, base: Path, file: RelPath = RelPath("log.txt")) -> Logger:
    ensure_dir_exists(base)
    logger = logging.getLogger(name)
    # inspired by default format for Rust env_logger
    formatter = logging.Formatter("[%(asctime)s %(levelname)s %(name)s] %(message)s")
    # https://stackoverflow.com/a/11582124/3882118
    fh = logging.FileHandler(base.joinpath(file))
    sh = logging.StreamHandler()
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.INFO)
    return logger

def open2(path: Path, mode: str) -> IO[Any]:
        ensure_dir_exists(path.parent)
        return open(path, mode)

def build_smaps_profiler():
    subprocess.run(["cargo", "build", "--release", "--manifest-path", project_root() / "smaps-profiler" / "Cargo.toml", ])

def create_experiment_files(base_path: Path):
    if base_path.exists():
        print(f"{base_path} exists; please remove it or use another output directory")
        sys.exit(1)
    build_smaps_profiler()
    info_path = base_path.joinpath("info.yaml")
    gen_info(info_path)
    with open2(base_path.joinpath("sys_argv"), 'w') as f:
        f.write(" ".join(sys.argv))
    # ChatGPT helped
    cmdline = open("/proc/self/cmdline", 'r').read().split('\0')
    cmdline = " ".join([c for c in cmdline])
    with open2(base_path.joinpath("cmdline"), 'w') as f:
        f.write(f"{os.getcwd()}$ ")
        f.write(cmdline)
    copy_project(base_path.joinpath("src"))

class ExitTimeouts:
    def __init__(self, warn: float, term: float, abrt: float):
        self.warn = warn
        self.term = term
        self.abrt = abrt

class App(AbstractContextManager["App", None]):
    def __init__(self, command: list[str], base_path: Path, logger: Logger, mem: int | None, exit_timeouts: ExitTimeouts = ExitTimeouts(20, 30, 40)):
        self.unit_name = str(uuid.uuid1())
        """
        --wait causes systemd-run to block until the service completes. This is useful so that we can just wait() on this process rather than continuously polling the service with `systemctl --user is-active {self.unit_name}`.
        ExitType=cgroup causes the service to complete only when all child processes of the application complete. https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html#ExitType=
        --collect "unload[s] the transient service" after it completes, so that it won't appear still in list-units. https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html#ExitType=
        We need a service rather than a scope here, and the reason is that we want to be able to send SIGTERM to just the main process to exit gracefully, but scopes don't have a main process. If SIGTERM takes too long, we still blast SIGKILL to every process, though.
        """
        self.systemd_proc = Popen(["systemd-run", "--user", f"--unit={self.unit_name}", "--collect", "--wait", "-p", "ExitType=cgroup", "-p", f"MemoryHigh={systemd_mem_str(mem)}"] + command)
        self.base_path = base_path
        self.logger = logger
        self.exit_timeouts = exit_timeouts

    def __enter__(self) -> Self:
        return self

    def send_signal(self, signal: int, whom: Literal["main", "all"]):
        """
        Rather than signalling self.systemd_proc itself, we want to send signals to processes in our transient service via systemctl. This is so that we can send a signal to and wait for every process in the application, not just the main one.
        """
        if self.is_running():
            subprocess.run(["systemctl", "--user", "kill", f"--kill-whom={whom}", f"--signal={signal}", self.unit_name])

    def terminate(self):
        self.send_signal(SIGTERM, "main")
    
    def kill(self):
        self.send_signal(SIGKILL, "all")
    
    def is_running(self) -> bool:
        return self.systemd_proc.poll() is None

    def wait(self):
        self.systemd_proc.wait()

    def stop(self) -> float:
        if not self.is_running():
            return 0
        abrt_sent = False
        kill_sent = False
        self.logger.info("sending SIGTERM")
        self.terminate()
        start = time.time()
        while True:
            duration = time.time() - start
            if not self.is_running():
                self.wait()
                return duration
            elif duration > self.exit_timeouts.abrt and not kill_sent:
                pyautogui.screenshot(self.base_path.joinpath("error_abort_timeout.png"))
                self.logger.warning("sending SIGKILL")
                self.kill()
                kill_sent = True
            elif duration > self.exit_timeouts.term and not abrt_sent:
                pyautogui.screenshot(self.base_path.joinpath("error_terminate_timeout.png"))
                self.logger.warning("sending SIGABRT")
                self.send_signal(SIGABRT, "main")
                abrt_sent = True
    
    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        took_long_time = False
        timeouts = self.exit_timeouts
        if self.stop() > timeouts.warn:
            took_long_time = True
        if took_long_time:
            raise TookLongTimeException

class Monitor(AbstractContextManager["Monitor", None]):
    def __init__(self, regex: str, base_path: Path, logger: Logger, graph_out: RelPath | str = "graph.svg", stdout_to_file: RelPath | str = "smaps_profiler.ndjson", check_if_running: bool = True):
        self.base_path = base_path
        self.logger = logger
        graph = base_path.joinpath(graph_out)
        stdout = base_path.joinpath(stdout_to_file)
        self.proc = start_monitor(regex, graph, stdout, check_if_running)

    def __enter__(self):
        return self

    def stop_monitor(self):
        self.proc.send_signal(SIGINT)
        self.proc.wait()

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self.stop_monitor()

class Context:
    """
    the purpose of this class is to hold a base path, a logger, and a memory amount.
    based on that info it provides convenience methods for starting apps (so that they
    start with the right memory and save their output to the right directory) and creating
    subdirectories (and subloggers).
    """
    def __init__(self, name: str, base_path: Path, logger: Logger, mem: int | None):
        self.name = name
        self.base_path = base_path
        self.logger = logger
        self.mem = mem

    @classmethod
    def from_module_with_mem(cls, name: str) -> "Context":
        # parse system arguments
        args = parse_sysargs_with_mem()

        # top-level experiment directory
        create_experiment_files(args.output_dir)

        # get logger
        logger = get_logger(name, args.output_dir)
        return Context(name, args.output_dir, logger, args.mem)

    @classmethod
    def from_module(cls, name: str) -> "Context":
        output_dir = parse_sysargs()
        create_experiment_files(output_dir)
        logger = get_logger(name, output_dir)
        return Context(name, output_dir, logger, None)

    def _get_child_logger(self, name: str) -> Logger:
        logger_name = f"{self.logger.name}.{name}"
        path = self.base_path.joinpath(name)
        return get_logger(logger_name, path)
 
    def get_child(self, name: str) -> "Context":
       return Context(name, self.base_path.joinpath(name), self._get_child_logger(name), self.mem)
    
    def get_child_with_mem(self, i: int, mem: int | None) -> "Context":
        name = f"{i:02d}_{mem}_bytes"
        return Context(name, self.base_path.joinpath(name), self._get_child_logger(name), mem)

    def get_child_with_sample(self, i: int) -> "Context":
        return Context.get_child(self, f"{i:02d}")

    def start_app(self, command: list[str], exit_timeouts: ExitTimeouts = ExitTimeouts(20, 30, 40)) -> App:
        return App(command, self.base_path, self.logger, self.mem, exit_timeouts)

    def monitor(self, regex: str, graph_out: RelPath | str = "graph.svg", stdout_to_file: RelPath | str = "smaps_profiler.ndjson", check_if_running: bool = True):
        return Monitor(regex, self.base_path, self.logger, graph_out, stdout_to_file, check_if_running)
    
    def screenshot(self, path: RelPath | str):
        pyautogui.screenshot(self.base_path.joinpath(path))

    def joinpath(self, path: RelPath | str) -> Path:
        return self.base_path.joinpath(path)

    def open(self, path: RelPath | str, mode: str) -> IO[Any]:
        return open2(self.joinpath(path), mode)

