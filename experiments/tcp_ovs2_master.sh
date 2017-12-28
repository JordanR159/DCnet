#!/bin/bash

echo -e "\n\n******************************************"
echo -e "Start the DCnetController on nebula102"
echo -e "Press ENTER to continue"
read x

# Remove the tcp_ovs2 directory from results and make a new one
rm -rf results/tcp_ovs2
mkdir -p results/tcp_ovs2

for i in `seq 1 5`
do
	# Remove the output directory
	rm -rf tcp_ovs2_output

	# Run the experiment
	./tcp_ovs2_experiment.sh

	# Move the output directory to results
	mv tcp_ovs2_output results/tcp_ovs2/run$i

	# Copy the plotscript and generation script to run directory
	cp tcp_ovs2_plotscript generate_tcp_ovs2_plot.sh results/tcp_ovs2/run$i
done
