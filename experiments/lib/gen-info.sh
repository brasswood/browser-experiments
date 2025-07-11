#!/bin/bash

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

if (( "$#" < 1 )); then
 	echo "Must supply an output file"
	exit 1
fi
KERNEL=$(uname -mrs)
# https://stackoverflow.com/a/58379307/3882118
DIST="$(sed -n 's/^NAME\=\"\([^"]*\)\"/\1/p' /etc/os-release) $(sed -n 's/^VERSION\=\"\([^"]*\)\"/\1/p' /etc/os-release)"
WSL="$(wsl.exe -v | tr -d '\0\r')"
if [[ "$WSL" ]]; then
	WSL_GPU="$(powershell.exe Get-CimInstance win32_VideoController)"
	WSL_GPU_NAME="$(echo "$WSL_GPU" | tr -d '\0\r' | grep "^Name" | cut -d":" -f 2 | tr -d " " )"
	WSL_GPU_DRIVER="$(echo "$WSL_GPU" | tr -d '\0\r' | grep "^DriverVersion" | cut -d":" -f 2 | tr -d " ")"
	WSL_SECTION="wsl_info: |
$(echo "$WSL" | sed 's/^/  /')
wsl_host_gpu_name: |
$(echo "$WSL_GPU_NAME" | sed 's/^/  /')
wsl_host_gpu_driver_version: |
$(echo "$WSL_GPU_DRIVER" | sed 's/^/  /')"
else
	WSL_SECTION="wsl_info: N/A
wsl_host_gpu_name: N/A
wsl_host_gpu_driver_version: N/A"
fi
HOST="$(uname -n)"
DATE="$(date -Iseconds)"
CPU="$(lscpu | sed -n 's/Model name: *\(.*\)/\1/p')"
# https://askubuntu.com/a/392944/346957
GPU_PCI="$(lspci | grep ' VGA ' | cut -d' ' -f 1)"
if [[ "$GPU_PCI" ]]; then
	GPU="$(lspci -v -s $(lspci | grep ' VGA ' | cut -d' ' -f 1))"
	# https://askubuntu.com/a/23240/346957
	# https://www.linuxquestions.org/questions/linux-kernel-70/how-to-change-the-vermagic-of-a-module-728387/#post3552205
	GPU_DRIVER="$(echo "$GPU" | sed -n 's/^\s*Kernel driver in use: \(.*\)$/\1/p')"
	GPU_DRIVER_VER="$(modinfo -F vermagic $GPU_DRIVER)"
	GPU_SECTION="gpu: |
$(echo "$GPU" | sed 's/^/  /')
gpu_driver:
  name: $GPU_DRIVER
  vermagic: $GPU_DRIVER_VER"
else
	GPU_SECTION="gpu: N/A
gpu_driver: N/A"
fi
MEMORY="$(sed -n 's/MemTotal: *\(.*\)/\1/p' /proc/meminfo)"
SWAP="$(sed -n 's/SwapTotal: *\(.*\)/\1/p' /proc/meminfo)"

echo "date: $DATE
host: $HOST
cpu: $CPU
ram: $MEMORY
swap: $SWAP
$GPU_SECTION
$WSL_SECTION
dist: $DIST
kernel: $KERNEL
app:
  name:
  version:
  source:
files:
description: describe your experimental procedure here
" > $1