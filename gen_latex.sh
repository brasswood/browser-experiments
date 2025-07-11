#!/bin/bash

cd ${1%"/"}
OUT="graphs.tex"

echo "
\\documentclass{article}
\\usepackage{graphicx} % Required for inserting images
\\usepackage{geometry}
\\usepackage{svg}
\\usepackage{lscape}
\\usepackage{subfig}
\\usepackage{rotating}
\\usepackage{relsize}
\\pagestyle{empty}
\\geometry{
    letterpaper,
    margin=0.5in}
\\newcommand{\\fig}[2]{\\subfloat[#1]{\\includesvg[width=0.33\\textwidth, pretex=\\relscale{0.3}]{#2}}}
\\begin{document}
" > $OUT
i=0
for graph in *.svg; do
	caption=$(echo ${graph%".svg"} | sed 's/_/\\_/g')
	if [[ $i == 0 ]]; then
		echo "
\\begin{sidewaysfigure}
    \\centering
" >> $OUT
	fi
	echo "    \\fig{$caption}{$graph}" >> $OUT
	if (( $i % 3 == 2 )); then
		echo "" >> $OUT # newline
	fi
	if [[ $i == 8 ]]; then
		echo "
\\end{sidewaysfigure}
\\newpage
" >> $OUT
	fi
	let i=($i+1)%9
done

if [[ $i != 0 ]]; then
	echo "
\\end{sidewaysfigure}
" >> $OUT
fi

echo "
\\end{document}
" >> $OUT
