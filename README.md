# Experiments
## Introduction
These scripts will run several GUI workloads and measure their memory consumption under various conditions.
Run them to verify (or dispute) the results of my master's thesis.

Your computer might look like it's possessed when these are running. Don't panic! This is just pyautogui automatically navigating stuff.

These scripts run a lot of tests and can take a long time. It may be a good idea to run them overnight.

**CAUTION:** All of the experiments besides browser_bench save screenshots. This is for diagnostic purposes if the script crashes.
If the screenshots contain personal information, delete them using `find` before sending them. They are all .png files.

## What it does
These are the programs that are tested:

- browserbench.org's speedometer 3.1
  - in chromium
  - in firefox

- Calendar apps
  - Google Calendar on Chromium
  - Google Calendar on Firefox
  - GNOME Calendar

- Chat apps
  - mov.im/chat on Chromium
  - mov.im/chat on Firefox
  - dino-im

- Mail apps
  - outlook.office365.com on Chromium
  - outlook.office365.com on Firefox
  - Evolution

The scripts compute a list of "memory constraints", then run each application 10 times for each memory constraint.
Memory constraints are applied using cgroups and their integration with systemd. The command these scripts run to
launch applications with constrained memory is `systemd-run --user --unit=<auto-generated uuid> --collect --wait -p ExitType=cgroup -p MemoryHigh=<memory limit> <command>` (found in `experiments/lib/__init__.py:App::__init__`). The
list of memory constraints to try is tunable; see the Tunable Parameters section.

The browserbench tests are run by `experiments/browser_bench/__init__.py` and invoked with the command `browser-bench`.
All of the other apps are run by `experiments/__init__.py` and invoked with the command `gui-apps`. For both of these
scripts, all data is placed in the directory specified by the first command line argument.

## Setup
I have tried to make running this easier by distributing it as a python package; however, there is still quite a bit of setup you will have to do to get it running properly. The following sections will describe it.

## System Requirements
These scripts have been tested on an Ubuntu MATE 24.04 computer running Python 3.13 from the nixos-24.11 repository.
They are known to not work on an Ubuntu 22.04 system running Python 3.10.

## Install Prerequisites
```console
$ sudo apt install gnuplot scrot xclip chromium-browser firefox dino-im gnome-calendar evolution evolution-ews
```

Additionally, make sure you have the rust toolchain installed: https://www.rust-lang.org/tools/install

## Clone this repository
**NOTE:** There is a submodule that you need to initialize.
```console
$ git clone --recurse-submodules https://github.com/brasswood/browser-experiments
```
or
```console
$ git clone https://github.com/brasswood/browser-experiments
$ cd browser-experiments
$ git submodule update --init --recursive
```

## Install this package
```console
$ pip install -e .
```

## Configure software

### Outlook (affects Firefox, Chrome, and Evolution)
- [ ] Create a folder called "Experiment" (without quotes) and copy or move a single message to that folder
- [ ] Make sure the message is not unread, and that the "Experiment" folder shows up in the sidebar of each mail client

### Firefox
- [ ] Create a new profile called "Experiments": https://support.mozilla.org/en-US/kb/profile-manager-create-remove-switch-firefox-profiles?redirectslug=profile-manager-create-and-remove-firefox-profiles&redirectlocale=en-US. Don't install any extensions in the new profile.
- [ ] Suppress "restore session" prompt: Go to about:config and set browser.sessionstore.resume_from_crash to false (https://support.mozilla.org/en-US/questions/1418488) 
- [ ] Suppress "safe mode" prompt: Go to about:config and set toolkit.startup.max_resumed_crashes to -1 (https://stackoverflow.com/a/21294259/3882118)

### Chromium
- [ ] Create a new profile with no extensions. It doesn't matter what it's called.
- [ ] Ensure that when you type `chromium` or `chromium-browser` at the command line, it opens straight to this new profile.

### Gnome Calendar
- [ ] Log in with an online account, preferably Google Calendar, or populate the calendar with some events

### Dino-im
- [ ] In a browser, create an account at mov.im
- [ ] Join the "Open Hardware Chat"
- [ ] Now open dino-im and log in to your new account

### Evolution
- [ ] Log in to an email account, preferably Microsoft Office 365
- Troubleshooting note on my machine: May get StartServiceByName timeout. If so, ON THE SAME DESKTOP SESSION, run busctl --user and confirm org.freedesktop.secrets is not running. Then start gnome-keyring-daemon --daemonize. See: https://superuser.com/q/1892770/749114

## Configure system
- [ ] Set system to dark theme. See why in the troubleshooting section.
- [ ] Configure the display to not go to sleep after inactivity.

## Final Checklist
Make sure you are logged into these websites and don't have to reenter your username and password after restarting the browsers:

- [ ] Chromium (make sure it launches to the new profile you created)
  - [ ] calendar.google.com
  - [ ] mov.im
  - [ ] outlook.office365.com

- [ ] Firefox
  - [ ] calendar.google.com
  - [ ] mov.im
  - [ ] outlook.office365.com

## Go!
Close all applications. Then:

```console
$ ./mega.sh
```

This will run the browserbench experiment (output directory: out/browser_bench), then the other
gui apps (output directory: out/gui_apps)

Try not to disturb your computer while the scripts are running.

To run an individual experiment in this package (example): python -m experiments.browser_bench <output_dir>

## Tunable Parameters
The memory constraints used can be tuned in both `experiments/browser_bench/__init__.py` and
`experiments/__init__.py`. The main constants are:

`RATE: float`: the factor to multiply the current memory constraint by to get the next memory constraint. Current setting: 0.8

`N: int`: number of memory constraints to try, including no memory constraint. Current setting: 17

`SAMPLES: int`: number of samples to take for each memory constraint. Current setting: 10

`DO_BASELINE: bool` (gui-apps only): for browsers, whether to open to about:blank for 30 seconds each sample to get the baseline
memory usage. Current setting: False

The initial memory constraint is always `None`, or no memory constraint. The first real memory constraint
is configured per-app in each of the scripts (e.g., `ExperimentParams(calendar_web, lib.decay(620 * MEGABYTE, RATE, N))`
in `experiments/__init__.py`, starts with a constraint of 620 MB.)

## Troubleshooting

`ImageNotFoundException`: This is expected to happen when the app starts thrashing and can't load fast enough. If the app is loading properly and you're getting this error, it means pyautogui can't find the button to click.

This python package includes images of the icons to click to navigate the interfaces; pyautogui then uses opencv to locate the icons on the screen and then click them. If the icons on your screen aren't a close enough match to the packaged icons, then the script will fail. This is why the instructions say to change your system to dark mode; I took pictures of the icons with my system in dark mode. If switching themes doesn't work, or you don't want to do it, then you'll have to either replace all of the screenshots of icons with your own, or give up on running this script. The icons are all .png files included in the various python subpackages. Note that you may need to get different images of the same icon for chromium and firefox, because each browser may render them slightly differently.
