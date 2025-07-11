#!/bin/bash

LIST=("nolimit" "2.0GiB" "1.0GiB" "512.0MiB" "256.0MiB" "128.0MiB" "64.0MiB" "32.0MiB" "16.0MiB" "8.0MiB" "4.0MiB" "2.0MiB" "1.0MiB")
DIGITS=$(echo "length (${#LIST[@]})" | bc)
cd ${1%"/"}

# https://stackoverflow.com/a/6723516/3882118
for i in "${!LIST[@]}"; do
	mem=${LIST[$i]}
	idx=$(printf "%0${DIGITS}d" "$i")
	for file in *_${mem}.svg; do
		mv $file ${file%"_${mem}.svg"}_${idx}_${mem}.svg
	done
done
