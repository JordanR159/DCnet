#!/bin/bash

# Remove the previous output and create a new directory
rm -rf tcp_control1_output/
mkdir tcp_control1_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
iperf3 -s -B dc98::9898:9800:4 -p 10001 --logfile tcp_control1_output/srv_rawop1 -D
iperf3 -s -B dc98::9898:9800:4 -p 10002 --logfile tcp_control1_output/srv_rawop2 -D

plotdata_file="tcp_control1_output/plotdata"
echo -e "#Delay(us)\tno-delay\tdelay" > $plotdata_file

# Delay values to test
delays=(0 200 400 600 800 1000 1200)

# Lines to skip in the raw output to get to the first run output
skip=19

for d in ${delays[*]}
do
	echo "delay is $d us"

	# Set the delay in nebula106
	ssh nebula106 "sudo tc qdisc change dev enp1s0f2 root handle 0: netem delay ${d}us"

	# Start the iperf3 clients
	ssh -f nebula111 "iperf3 -c dc98::9898:9800:4 -p 10001 -O 10 -t 15 > /dev/null"
	ssh -f nebula112 "iperf3 -c dc98::9898:9800:4 -p 10002 -O 10 -t 15 > /dev/null"

	# Wait until the test finishes
	sleep 30

	# Compute the average for client1
	total=0
	avg1=0
	for val in $(cat tcp_control1_output/srv_rawop1 | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_control1_output/throughput_d${d}_nodelay
		total=`echo $total+$val | bc`
	done
	avg1=$(echo $total/10 | bc -l)

	# Compute the average for client 2
	total=0
	for val in $(cat tcp_control1_output/srv_rawop2 | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_control1_output/throughput_d${d}_delay
		total=`echo $total+$val | bc`
	done
	avg2=$(echo $total/10 | bc -l)

	# Write the values in the plotdata file
	echo -e "${d}\t${avg1}\t${avg2}" >> $plotdata_file

	# Lines to skip in the raw output to get to the next run
	skip=`expr $skip + 36`
done

# Kill the server
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done
