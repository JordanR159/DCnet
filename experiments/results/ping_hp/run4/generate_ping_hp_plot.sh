#!/bin/bash

gnuplot ping_hp_plotscript
#epstopdf ping_hp_plot.eps
convert ping_hp_plot.png ping_hp_plot.jpg
