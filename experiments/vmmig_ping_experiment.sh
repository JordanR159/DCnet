#!/bin/bash

# Remove previous output and create a new directory
rm -rf vmmig_ping_output
mkdir -p vmmig_ping_output

# Starting UID
uid=8

# Get the starting UID from command line if provided
if [ $# -gt 0 ]
then
	uid=$1
fi

# No. of ToR switches
tors=(1000 2000 3000 4000 5000 6000 7000 8000 9000 10000)

echo -e "#ToRs\tRun1\tRun2\tRun3\tRun4\tRun5\tAvg" > vmmig_ping_output/plotdata_noopt
echo -e "#ToRs\tRun1\tRun2\tRun3\tRun4\tRun5\tAvg" > vmmig_ping_output/plotdata_opt

# Run experiments with no optimization
for t in ${tors[*]}
do

	echo -n -e "${t}\t" >> vmmig_ping_output/plotdata_noopt

	total=0
	avg=0
	min=10001
	max=0

	# Run 5 experiments for each #ToR
	for i in `seq 1 5`
	do

		# Create a VM
		curl -X PUT -d "{ \"server\":\"dcnet-srv000\" }" http://nebula102:8080/DCnet/create-vm

		# Let the VM come up
		sleep 8

		# Remove the "lost" results from previous run
		rm -rf vmmig_ping_output/.lost

		# Start Pinging
		sudo ./DCnetPing ${uid} -o vmmig_ping_output/resptimes_noopt_t${t}_${i} > vmmig_ping_output/.lost &

		# Sleep for 2 seconds
		sleep 2

		# Move the VM
		curl -X PUT -d "{ \"uid\":${uid}, \"dst\":\"dcnet-srv100\", \"optimize\":0, \"n_tor\":${t} }" http://nebula102:8080/DCnet/migrate-vm

		# Wait for the pings to stop
		sleep 25

		# Add the #lost to the total
		lost=`cat vmmig_ping_output/.lost`
		total=`echo "$total + $lost" | bc -l`

		# Update the min and max
		if [ $min -gt $lost ]
		then
			min=$lost
		fi

		if [ $max -lt $lost ]
		then
			max=$lost
		fi

		# Write the result for this run in the plotdata file
		echo -n -e "${lost}\t" >> vmmig_ping_output/plotdata_noopt

		# Delete the VM
		curl -X PUT -d "{ \"uid\":${uid} }" http://nebula102:8080/DCnet/delete-vm

		uid=`echo "$uid + 1" | bc`
	done

	avg=`echo "$total/5" | bc -l`
	echo -e "${avg}\t${min}\t${max}" >> vmmig_ping_output/plotdata_noopt
done

# Run experiments with optimization
for t in ${tors[*]}
do

	echo -n -e "${t}\t" >> vmmig_ping_output/plotdata_opt

	total=0
	avg=0
	min=10001
	max=0

	# Run 5 experiments for each #ToR
	for i in `seq 1 5`
	do

		# Create a VM
		curl -X PUT -d "{ \"server\":\"dcnet-srv000\" }" http://nebula102:8080/DCnet/create-vm

		# Let the VM come up
		sleep 8

		# Remove the "lost" results from previous run
		rm -rf vmmig_ping_output/.lost

		# Start Pinging
		sudo ./DCnetPing ${uid} -o vmmig_ping_output/resptimes_opt_t${t}_${i} > vmmig_ping_output/.lost &

		# Sleep for 2 seconds
		sleep 2

		# Move the VM
		curl -X PUT -d "{ \"uid\":${uid}, \"dst\":\"dcnet-srv100\", \"optimize\":1, \"n_tor\":${t} }" http://nebula102:8080/DCnet/migrate-vm

		# Wait for the pings to stop
		sleep 25

		# Add the #lost to the total
		lost=`cat vmmig_ping_output/.lost`
		total=`echo "$total + $lost" | bc -l`

		# Update the min and max
		if [ $min -gt $lost ]
		then
			min=$lost
		fi

		if [ $max -lt $lost ]
		then
			max=$lost
		fi

		# Write the result for this run in the plotdata file
		echo -n -e "${lost}\t" >> vmmig_ping_output/plotdata_opt

		# Delete the VM
		curl -X PUT -d "{ \"uid\":${uid} }" http://nebula102:8080/DCnet/delete-vm

		uid=`echo "$uid + 1" | bc`
	done

	avg=`echo "$total/5" | bc -l`
	echo -e "${avg}\t${min}\t${max}" >> vmmig_ping_output/plotdata_opt
done
