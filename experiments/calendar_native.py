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

#!/usr/bin/python3
import time
from .lib import Experiment, Context

def run_experiment(ex: Context) -> None:
    with ex:
        # Run experiment
        ex.start_monitor("gnome-calendar")
        ex.start(["gnome-calendar"])
        time.sleep(30)
        ex.screenshot()

def main() -> None:
    with Experiment.parse_sysargs() as ex:
        run_experiment(ex)

if __name__ == "__main__":
    main()
