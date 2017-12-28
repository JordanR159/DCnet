#!/bin/bash

echo -e "\n\n******************************************"
echo -e "Start the DCnetController on nebula102"
echo -e "Press ENTER to continue"
read x

# Remove the tcp_ovs1 directory from results and make a new one
rm -rf results/tcp_ovs1
mkdir -p results/tcp_ovs1

for i in `seq 1 5`
do
	# Remove the output directory
	rm -rf tcp_ovs1_output

	# Run the experiment
	./tcp_ovs1_experiment.sh

	# Move the output directory to results
	mv tcp_ovs1_output results/tcp_ovs1/run$i

	# Copy the plotscript and generation script to run directory
	cp tcp_ovs1_plotscript generate_tcp_ovs1_plot.sh results/tcp_ovs1/run$i
done
