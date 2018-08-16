#!/bin/bash

gnuplot ping_ovs_plotscript
#epstopdf ping_ovs_plot.eps
convert ping_ovs_plot.png ping_ovs_plot.jpg
