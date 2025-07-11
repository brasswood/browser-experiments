#!/bin/bash

shopt -s extglob

OUTPUT=${1%"/"}
for dir in $OUTPUT/!("graphs_all"|"errors.log"); do
	cp $dir/graph.svg $OUTPUT/graphs_all/$(basename $dir).svg;
done
