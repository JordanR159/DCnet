#!/bin/bash

gnuplot ping_ovs_nojump_plotscript
#epstopdf ping_ovs_nojump_plot.eps
convert ping_ovs_nojump_plot.png ping_ovs_nojump_plot.jpg
