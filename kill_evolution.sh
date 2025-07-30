#!/usr/bin/env bash

systemctl --user stop evolution-addressbook-factory.service
systemctl --user stop evolution-calendar-factory.service
systemctl --user stop evolution-source-registry.service
systemctl --user stop evolution-user-prompter.service
pkill -f evolution-alarm-notify