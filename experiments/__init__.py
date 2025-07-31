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
from . import calendar_web, calendar_firefox, calendar_native, chat_web, chat_firefox, chat_native, mail_web, mail_firefox, mail_native, blank_web, blank_firefox
from .lib import MEGABYTE, Context, TookLongTimeException
from . import lib

class ExperimentParams:
    def __init__(self, module: ModuleType, mems: List[int | None] = [None]) -> None:
        self.module = module
        self.mems = mems
    def name(self) -> str:
        return self.module.__name__.split('.')[-1]

RATE = 0.8
N = 17
# N = 1
SAMPLES = 10
# SAMPLES = 1
DO_BASELINE=False

ALL_MEM: list[ExperimentParams] = [
    ExperimentParams(blank_web, lib.decay(410 * MEGABYTE, RATE, N)),
    ExperimentParams(blank_firefox, lib.decay(470 * MEGABYTE, RATE, N)),
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
    with Context.from_module("classic") as top_ctx, top_ctx.get_child("out") as out_ctx:
        for params in experiments:
            with out_ctx.get_child(params.name()) as ex_ctx:
                for (i, mem) in enumerate(params.mems):
                    took_long_time = False
                    with ex_ctx.get_child_with_mem(i, mem) as mem_ctx:
                        for j in range(SAMPLES):
                            with mem_ctx.get_child_with_sample(j) as sample_ctx:
                                try:
                                    params.module.run_experiment(sample_ctx, do_baseline=DO_BASELINE)
                                except TookLongTimeException as e:
                                    sample_ctx.logger.warning(f"Application took longer than {e.warn_time} seconds to exit. Refusing to reduce memory any more for this workload.")
                                    took_long_time = True
                                except Exception as e:
                                    sample_ctx.logger.exception(e)
                            if took_long_time:
                                break
