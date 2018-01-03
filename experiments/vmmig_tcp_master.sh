#!/bin/bash

# Remove the previous results and create a new directory
rm -rf results/vmmig_tcp
mkdir -p results/vmmig_tcp

uid=8

for i in `seq 1 5`
do
	# Remove previous output
	rm -rf vmmig_tcp_output

	# Run the experiment
	./vmmig_tcp_experiment.sh $uid

	# Move the output to results
	mv vmmig_tcp_output results/vmmig_tcp/run$i

	# Copy plot generation scripts
	cp vmmig_tcp_plotscript generate_vmmig_tcp_plot.sh results/vmmig_tcp/run$i/

	uid=`echo "$uid + 2" | bc`
done
