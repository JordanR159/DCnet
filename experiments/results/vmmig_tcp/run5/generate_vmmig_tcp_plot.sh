#!/bin/bash

gnuplot vmmig_tcp_plotscript
#epstopdf vmmig_tcp_plot.eps
convert vmmig_tcp_plot.png vmmig_tcp_plot.jpg
