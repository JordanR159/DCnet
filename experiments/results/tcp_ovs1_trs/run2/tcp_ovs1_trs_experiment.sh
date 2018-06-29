#!/bin/bash

# Remove the previous output and create a new directory
rm -rf tcp_ovs1_trs_output/
mkdir tcp_ovs1_trs_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
iperf3 -s -B dc98::d4ae:52c8:c361 -A 0 --logfile tcp_ovs1_trs_output/srv_rawop1 -D
iperf3 -s -B dc91::9191:9100:4 -A 0 --logfile tcp_ovs1_trs_output/srv_rawop2 -D

plotdata_file="tcp_ovs1_trs_output/plotdata"
echo -e "#Delay(us)\trewriting\ttunneling" > $plotdata_file

# MTU values to test
mtus=(1500 2000 3000 4000 5000 6000 7000 8000 8930)

# Lines to skip in the raw output to get to the first run output
skip=19

for m in ${mtus[*]}
#for m in `seq 1000 1000 8000`
do
	echo "MTU is $m"

	# Set the MTU on n111, n112, n113
	#ssh nebula111 "sudo ifconfig hyp mtu $m; sudo ifconfig hyp-conn mtu $m; sudo ifconfig eth1 mtu $m"
	#ssh nebula112 "sudo ifconfig vxlan1 mtu $m"
	#sudo ifconfig hyp mtu $m; sudo ifconfig hyp-conn mtu $m; sudo ifconfig em2 mtu $m
	#sudo ifconfig vxlan1 mtu $m

	ssh nebula111 "sudo ifconfig dcnet-srv000 mtu $m"
	ssh nebula111 "sudo ifconfig eth1 mtu $m"
	sudo ifconfig em2 mtu $m

	# Start the iperf3 clients
	ssh -f nebula111 "iperf3 -c dc98::d4ae:52c8:c361 -M $m -t 25 -Z -A 0 > /dev/null"

	sleep 30

	ssh nebula111 "sudo ifconfig dcnet-srv000 mtu 9000"
	ssh nebula111 "sudo ifconfig eth1 mtu 9000"
	ssh nebula111 "sudo ifconfig vxlan1 mtu $m"
	sudo ifconfig em2 mtu 9000

	ssh -f nebula111 "iperf3 -c dc91::9191:9100:4 -M $m -t 25 -Z -A 0 > /dev/null"

	# Wait until the test finishes
	sleep 30

	# Compute the average for rewriting case
	total=0
	avg1=0
	for val in $(cat tcp_ovs1_trs_output/srv_rawop1 | grep -v "OUT OF ORDER" | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_ovs1_trs_output/throughput_m${m}_rewriting
		total=`echo $total+$val | bc`
	done
	avg1=$(echo $total/10 | bc -l)

	# Compute the average for tunneling case
	total=0
	for val in $(cat tcp_ovs1_trs_output/srv_rawop2 | grep -v "OUT OF ORDER" | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> tcp_ovs1_trs_output/throughput_m${m}_tunneling
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
