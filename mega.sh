#!/bin/bash
# Commented out lines are to reduce noise on my own system
# systemctl --user disable backup.timer
# systemctl --user stop onedrive.service

# . ./kill_evolution.sh

python -m experiments.browser_bench out/browser_bench
python -m experiments out/gui_apps

# systemctl --user enable backup.timer
# systemctl --user start onedrive.service
