#!/bin/bash

echo -e "\n\n******************************************"
echo -e "Start the DCnetController on nebula102"
echo -e "Press ENTER to continue"
read x

# Remove the tcp_control2 directory from results and make a new one
rm -rf results/tcp_control2
mkdir -p results/tcp_control2

for i in `seq 1 5`
do
	# Remove the output directory
	rm -rf tcp_control2_output

	# Run the experiment
	./tcp_control2_experiment.sh

	# Move the output directory to results
	mv tcp_control2_output results/tcp_control2/run$i

	# Copy the plotscript and generation script to run directory
	cp tcp_control2_plotscript generate_tcp_control2_plot.sh results/tcp_control2/run$i
done
