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
from .lib import Context
import subprocess

def get_version() -> str:
    return str(subprocess.run(["gnome-calendar", "--version"], capture_output=True).stdout)

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    with ctx.monitor("gnome-calendar"), ctx.start_app(["gnome-calendar"]):
        # Run experiment
        time.sleep(30)
        ctx.screenshot("app.png")

def main() -> None:
        run_experiment(Context.from_module_with_mem(__name__), True)

if __name__ == "__main__":
    main()
