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
import signal

def run_experiment(ctx: Context, do_baseline: bool) -> None:
    # Well this sucks
    subprocess.run(["systemctl", "--user", "stop", "evolution-addressbook-factory.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-calendar-factory.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-source-registry.service"])
    subprocess.run(["systemctl", "--user", "stop", "evolution-user-prompter.service"])
    subprocess.run(["pkill", "-f", "evolution-alarm-notify"])
    with ctx.monitor("evolution"):
        with ctx.start_app(["evolution"]) as app:
            # Run experiment
            time.sleep(30)
            ctx.screenshot("app.png")
            app.terminate() # terminate main process
            app.send_signal(signal.SIGTERM, 'all') # terminate all processes (evolution is so stubborn)

def main() -> None:
    run_experiment(Context.from_module_with_mem(__name__), True)

if __name__ == "__main__":
    main()
