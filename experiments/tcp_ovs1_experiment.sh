#!/bin/bash

# Remove the previous output and create a new directory
rm -rf tcp_ovs1_output/
mkdir tcp_ovs1_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
iperf3 -s -B dc98::9898:9800:4 --logfile tcp_ovs1_output/srv_rawop1 -D
iperf3 -s -B dc99::9999:9900:4 --logfile tcp_ovs1_output/srv_rawop2 -D

plotdata_file="tcp_ovs1_output/plotdata"
echo -e "#Delay(us)\tno-rewriting\trewriting" > $plotdata_file

# MTU values to test
mtus=(3000 5000 7000 9000)

# Lines to skip in the raw output to get to the first run output
skip=19

for m in ${mtus[*]}
do
	echo "MTU is $m us"

	# Set the MTU on n111, n112, n113
	ssh nebula111 "sudo ifconfig hyp mtu $m; sudo ifconfig hyp-conn mtu $m; sudo ifconfig eth1 mtu $m"
	ssh nebula112 "sudo ifconfig hyp mtu $m; sudo ifconfig hyp-conn mtu $m; sudo ifconfig eno2 mtu $m"
	sudo ifconfig hyp mtu $m; sudo ifconfig hyp-conn mtu $m; sudo ifconfig em2 mtu $m

	# Start the iperf3 clients
	ssh -f nebula111 "iperf3 -c dc98::9898:9800:4 -O 10 -t 15 > /dev/null"
	ssh -f nebula112 "iperf3 -c dc99::9999:9900:4 -O 10 -t 15 > /dev/null"

	# Wait until the test finishes
	sleep 30

	# Compute the average for client1
	total=0
	avg1=0
	for val in $(cat tcp_ovs1_output/srv_rawop1 | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_ovs1_output/throughput_m${m}_norewriting
		total=`echo $total+$val | bc`
	done
	avg1=$(echo $total/10 | bc -l)

	# Compute the average for client 2
	total=0
	for val in $(cat tcp_ovs1_output/srv_rawop2 | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_ovs1_output/throughput_m${m}_rewriting
		total=`echo $total+$val | bc`
	done
	avg2=$(echo $total/10 | bc -l)

	# Write the values in the plotdata file
	echo -e "${m}\t${avg1}\t${avg2}" >> $plotdata_file

	# Lines to skip in the raw output to get to the next run
	skip=`expr $skip + 36`
done

# Kill the server
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done
