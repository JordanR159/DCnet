#!/bin/bash

gnuplot tcp_control1_plotscript
#epstopdf tcp_control1_plot.eps
convert tcp_control1_plot.png tcp_control1_plot.jpg
