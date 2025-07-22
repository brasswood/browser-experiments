#!/bin/bash
systemctl --user disable backup.timer

systemctl --user stop evolution-addressbook-factory.service
systemctl --user stop evolution-calendar-factory.service
systemctl --user stop evolution-source-registry.service
systemctl --user stop evolution-user-prompter.service

python -m experiments.browser_bench out/browser_bench
python -m experiments out/classic

systemctl --user enable backup.timer
