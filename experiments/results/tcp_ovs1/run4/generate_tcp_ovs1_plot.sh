#!/bin/bash

gnuplot tcp_ovs1_plotscript
#epstopdf tcp_ovs1_plot.eps
convert tcp_ovs1_plot.png tcp_ovs1_plot.jpg
