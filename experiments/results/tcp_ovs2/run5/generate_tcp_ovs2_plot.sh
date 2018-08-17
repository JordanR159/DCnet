#!/bin/bash

gnuplot tcp_ovs2_plotscript
#epstopdf tcp_ovs2_plot.eps
convert tcp_ovs2_plot.png tcp_ovs2_plot.jpg
