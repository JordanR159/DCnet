#!/bin/bash

# Remove the ping_ovs directory from results
rm -rf results/ping_ovs

# Make the directory ping_ovs under results
mkdir -p results/ping_ovs

for i in `seq 1 5`
do
	# Remove the ping_ovs_output directory
	rm -rf ping_ovs_output

	# Run the experiment
	./ping_ovs_experiment.sh

	# Move the output to the results directory
	mv ping_ovs_output results/ping_ovs/run$i

	# Copy the gnuplot-plotscript and plot generation script to run directory
	cp ping_ovs_plotscript generate_ping_ovs_plot.sh results/ping_ovs/run$i/
done
