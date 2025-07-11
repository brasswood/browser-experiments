#!/bin/bash

cd ${1%"/"}
pdflatex -shell-escape -interaction nonstopmode graphs.tex
