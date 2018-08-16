#!/bin/bash

gnuplot tcp_control2_plotscript
#epstopdf tcp_control2_plot.eps
convert tcp_control2_plot.png tcp_control2_plot.jpg
