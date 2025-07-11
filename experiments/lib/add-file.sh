#!/bin/bash
if (( "$#" < 3 )); then
	echo "Must supply at least one input file"
	exit 1
fi
# https://stackoverflow.com/a/1854031/3882118
OUTDIR=${@: -2:1}
OUTFILE=${@: -1:1}
# OUTFILE="info.yaml"
if [ ! -f "$OUTFILE" ]; then
	echo "Error: $OUTFILE not found."
	exit 1
fi
# https://unix.stackexchange.com/a/353835/703626
# for file in ${@:1:$#-1}
for file in ${@:1:$#-2}
do
	if [ -f "$file" ]; then
		cp $file $OUTDIR
		# https://stackoverflow.com/a/7680548/3882118
		sed -i 's/^files: *$/files:\n  - name: '"$(basename $file)"'\n    sha1: '"$(sha1sum $file | cut -d ' ' -f 1)"'/' $OUTFILE
	else
		echo "Warning: $file does not exist or is not a file."
	fi
done
