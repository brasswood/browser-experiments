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

import time
from ..lib import Experiment, Context, load_page

def run_experiment(ex: Context) -> None:
    ex.start_monitor("firefox")
    ex.start(["firefox", "-P", "Experiments", "about:blank"])
    # wait 30 on the blank page
    time.sleep(30)
    ex.screenshot("blank.png")
    load_page("firefox", 'outlook.office365.com')
    # wait another 30
    time.sleep(30)
    ex.screenshot("app.png")

def main() -> None:
    with Experiment.parse_sysargs() as ex:
        run_experiment(ex)
