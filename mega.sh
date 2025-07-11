#!/bin/bash
systemctl --user stop evolution-addressbook-factory.service
systemctl --user stop evolution-calendar-factory.service
systemctl --user stop evolution-source-registry.service
systemctl --user stop evolution-user-prompter.service

python -m experiments.browser_bench out/out_browser_bench
python -m experiments.classic_with_samples out/out_classic_with_samples