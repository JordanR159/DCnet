#!/bin/bash

echo -e "\n\n******************************************"
echo -e "Start the DCnetController on nebula102"
echo -e "Press ENTER to continue"
read x

# Remove the tcp_control1 directory from results and make a new one
rm -rf results/tcp_control1
mkdir -p results/tcp_control1

for i in `seq 1 5`
do
	# Remove the output directory
	rm -rf tcp_control1_output

	# Run the experiment
	./tcp_control1_experiment.sh

	# Move the output directory to results
	mv tcp_control1_output results/tcp_control1/run$i

	# Copy the plotscript and generation script to run directory
	cp tcp_control1_plotscript generate_tcp_control1_plot.sh results/tcp_control1/run$i
done
