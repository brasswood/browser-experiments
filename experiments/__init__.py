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

from typing import List
from types import ModuleType
from pathlib import Path
from . import calendar_web, calendar_firefox, calendar_native, chat_web, chat_firefox, chat_native, mail_web, mail_firefox, mail_native
import sys
import os
import shutil
from .lib import human_mem_str, Experiment, TookLongTimeException

class ExperimentParams:
    def __init__(self, module: ModuleType, mems: List[int | None] = [None]) -> None:
        self.module = module
        self.mems = mems
    def name(self) -> str:
        return self.module.__name__

ALL_CHROME: list[ExperimentParams] = [
    ExperimentParams(calendar_web),
    ExperimentParams(calendar_native),
    ExperimentParams(chat_web),
    ExperimentParams(chat_native),
    ExperimentParams(mail_web),
    ExperimentParams(mail_native),
]

ALL: list[ExperimentParams] = [
    ExperimentParams(calendar_web),
    ExperimentParams(calendar_firefox),
    ExperimentParams(calendar_native),
    ExperimentParams(chat_web),
    ExperimentParams(chat_firefox),
    ExperimentParams(chat_native),
    ExperimentParams(mail_web),
    ExperimentParams(mail_firefox),
    ExperimentParams(mail_native),
]

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

RATE: float = 0.7
N: int = 10

ALL_MEM: list[ExperimentParams] = [
    ExperimentParams(calendar_web, decay(620 * MEGABYTE, RATE, N)),
    ExperimentParams(calendar_firefox, decay(820 * MEGABYTE, RATE, N)),
    ExperimentParams(calendar_native, decay(130 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_web, decay(520 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_firefox, decay(520 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_native, decay(230 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_web, decay(870 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_firefox, decay(980 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_native, decay(310 * MEGABYTE, RATE, N)),
]

def parse_sysargs() -> Path:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_directory>")
        sys.exit(1)
    return Path(sys.argv[1])

def run_all(experiments: list[ExperimentParams]=ALL_MEM) -> None:
    output_dir = parse_sysargs()
    graphs_dir = output_dir.joinpath("graphs_all")
    os.makedirs(graphs_dir)
    for params in experiments:
        name_dir = output_dir.joinpath(params.name())
        os.makedirs(name_dir)
        for (i, mem) in enumerate(params.mems):
            mem_dir = name_dir.joinpath("{:02d}_{}".format(i, human_mem_str(mem)))
            os.makedirs(mem_dir)
            for j in range(10):
                fullpath = mem_dir.joinpath(str(j))
                ex = Experiment(params.name(), fullpath, mem, None)
                try:
                    params.module.run_experiment(ex)
                    path_2 = "{}_{}_{:02d}_{}".format(params.name(), j, i, human_mem_str(mem))
                    shutil.copy(fullpath.joinpath("graph.svg"), graphs_dir.joinpath(path_2 + ".svg"))
                except TookLongTimeException:
                    ex.m_logger.warning("Application took longer than 25 seconds to exit. Refusing to reduce memory any more for this workload.")
                except Exception:
                    pass
