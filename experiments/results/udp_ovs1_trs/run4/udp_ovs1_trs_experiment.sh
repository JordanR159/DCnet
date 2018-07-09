#!/bin/bash

# Remove the previous output and create a new directory
rm -rf udp_ovs1_trs_output/
mkdir udp_ovs1_trs_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
iperf3 -s -B dc98::d4ae:52c8:c361 --logfile udp_ovs1_trs_output/srv_rawop1 -A 0 -D
iperf3 -s -B dc91::9191:9100:4 --logfile udp_ovs1_trs_output/srv_rawop2 -A 0 -D

plotdata_file="udp_ovs1_trs_output/plotdata"
plotdata_cpu_file="udp_ovs1_trs_output/plotdata_cpu"

echo -e "#PacketSize\trewriting\ttunneling" > $plotdata_file
echo -e "#PacketSize\trewriting\ttunneling" > $plotdata_cpu_file

# Payload sizes to test
sizes=(50 300 1500 4000 8000)

# Lines to skip in the raw output to get to the first run output
skip=19

for m in ${sizes[*]}
#for m in `seq 1000 1000 8000`
do
	echo "Payload size is $m"

	# Start the iperf3 clients
	ssh -f nebula111 "iperf3 -c dc98::d4ae:52c8:c361 -l $m -t 25 -Z -u -b 0 -A 0 > /dev/null"

	ssh -f nebula111 "pidstat -G iperf3 20 1" > udp_ovs1_trs_output/cpu_m${m}_rewriting_rawop

	sleep 30

	ssh -f nebula111 "iperf3 -c dc91::9191:9100:4 -l $m -t 25 -Z -u -b 0 -A 0 > /dev/null"

	ssh -f nebula111 "pidstat -G iperf3 20 1" > udp_ovs1_trs_output/cpu_m${m}_tunneling_rawop

	# Wait until the test finishes
	sleep 30

	# CPU utilization
	cpu1=`cat udp_ovs1_trs_output/cpu_m${m}_rewriting_rawop | tail -1 | gawk '{print $7}'`
	cpu2=`cat udp_ovs1_trs_output/cpu_m${m}_tunneling_rawop | tail -1 | gawk '{print $7}'`

	echo -e "${m}\t${cpu1}\t${cpu2}" >> $plotdata_cpu_file

	# Compute the average for rewriting case
	total=0
	avg1=0
	for val in $(cat udp_ovs1_trs_output/srv_rawop1 | grep -v "OUT OF ORDER" | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> udp_ovs1_trs_output/throughput_m${m}_rewriting
		total=`echo $total+$val | bc`
	done
	avg1=$(echo $total/10 | bc -l)

	# Compute the average for tunneling case
	total=0
	for val in $(cat udp_ovs1_trs_output/srv_rawop2 | grep -v "OUT OF ORDER" | tail -n +$skip | head -n 10 | gawk '{print $7}')
	do
		echo $val >> udp_ovs1_trs_output/throughput_m${m}_tunneling
		total=`echo $total+$val | bc`
	done
	avg2=$(echo $total/10 | bc -l)

	# Write the values in the plotdata file
	echo -e "${m}\t${avg1}\t${avg2}" >> $plotdata_file

	# Lines to skip in the raw output to get to the next run
	skip=`expr $skip + 35`
done

# Kill the server
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done
