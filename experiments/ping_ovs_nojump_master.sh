#!/bin/bash

# Remove the ping_ovs_nojump directory from results
rm -rf results/ping_ovs_nojump

# Make the directory ping_ovs_nojump under results
mkdir -p results/ping_ovs_nojump

for i in `seq 1 5`
do
	# Remove the ping_ovs_nojump_output directory
	rm -rf ping_ovs_nojump_output

	# Run the experiment
	./ping_ovs_nojump_experiment.sh

	# Move the output to the results directory
	mv ping_ovs_nojump_output results/ping_ovs_nojump/run$i

	# Copy the gnuplot-plotscript and plot generation script to run directory
	cp ping_ovs_nojump_plotscript generate_ping_ovs_nojump_plot.sh results/ping_ovs_nojump/run$i/
done
