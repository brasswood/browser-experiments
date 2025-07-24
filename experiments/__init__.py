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
from . import calendar_web, calendar_firefox, calendar_native, chat_web, chat_firefox, chat_native, mail_web, mail_firefox, mail_native
import shutil
from .lib import MEGABYTE, Context, TookLongTimeException
from . import lib

class ExperimentParams:
    def __init__(self, module: ModuleType, mems: List[int | None] = [None]) -> None:
        self.module = module
        self.mems = mems
    def name(self) -> str:
        return self.module.__name__.split('.')[-1]

RATE = 0.9
N = 50
# N = 1
SAMPLES = 10
# SAMPLES = 1

ALL_MEM: list[ExperimentParams] = [
    ExperimentParams(calendar_web, lib.decay(620 * MEGABYTE, RATE, N)),
    ExperimentParams(calendar_firefox, lib.decay(820 * MEGABYTE, RATE, N)),
    ExperimentParams(calendar_native, lib.decay(130 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_web, lib.decay(520 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_firefox, lib.decay(520 * MEGABYTE, RATE, N)),
    ExperimentParams(chat_native, lib.decay(230 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_web, lib.decay(870 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_firefox, lib.decay(980 * MEGABYTE, RATE, N)),
    ExperimentParams(mail_native, lib.decay(310 * MEGABYTE, RATE, N)),
]

def run_all(experiments: list[ExperimentParams]=ALL_MEM) -> None:
    top_ctx = Context.from_module("classic")
    graphs_dir = top_ctx.joinpath("graphs_all")
    lib.ensure_dir_exists(graphs_dir)
    for params in experiments:
        ex_ctx = top_ctx.get_child(params.name())
        for (i, mem) in enumerate(params.mems):
            took_long_time = False
            mem_ctx = ex_ctx.get_child_with_mem(i, mem)
            for j in range(SAMPLES):
                sample_ctx = mem_ctx.get_child_with_sample(j)
                try:
                    params.module.run_experiment(sample_ctx)
                    shutil.copy2(sample_ctx.joinpath("graph.svg"), graphs_dir.joinpath(f"{ex_ctx.name}_{mem_ctx.name}_{sample_ctx.name}.svg"))
                except TookLongTimeException:
                    sample_ctx.logger.warning("Application took longer than 25 seconds to exit. Refusing to reduce memory any more for this workload.")
                    took_long_time = True
                except Exception:
                    pass
            if took_long_time:
                continue
