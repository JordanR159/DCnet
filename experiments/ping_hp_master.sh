#!/bin/bash

# Remove the ping_hp directory from results
rm -rf results/ping_hp

# Make the directory ping_hp under results
mkdir -p results/ping_hp

for i in `seq 1 5`
do
	# Remove the ping_hp_output directory
	rm -rf ping_hp_output

	# Run the experiment
	./ping_hp_experiment.sh

	# Move the output to the results directory
	mv ping_hp_output results/ping_hp/run$i

	# Copy the gnuplot-plotscript and plot generation script to run directory
	cp ping_hp_plotscript generate_ping_hp_plot.sh results/ping_hp/run$i/
done
