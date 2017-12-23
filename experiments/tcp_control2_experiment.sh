#!/bin/bash

# Remove the previous output and create a new directory
rm -rf tcp_control2_output/
mkdir -p tcp_control2_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
echo "Starting the servers..."
iperf3 -s -B dc98::9898:9800:4 -p 10001 --logfile tcp_control2_output/srv_rawop1 -D
iperf3 -s -B dc98::9898:9800:4 -p 10002 --logfile tcp_control2_output/srv_rawop2 -D

plotdata_file_nodelay="tcp_control2_output/plotdata_nodelay"
plotdata_file_delay="tcp_control2_output/plotdata_delay"
echo "#no-delay" > $plotdata_file_nodelay
echo "#with-delay" > $plotdata_file_delay

# Delay values to test
delays=(0 200 400 600 800 1000 1200)

# Start the clients
echo "Starting the clients..."
ssh -f nebula111 "iperf3 -c dc98::9898:9800:4 -p 10001 -O 10 -t 80 > /dev/null"
ssh -f nebula112 "iperf3 -c dc98::9898:9800:4 -p 10002 -O 10 -t 80 > /dev/null"

sleep 12

for d in ${delays[*]}
do
	echo "delay: ${d} us"

	# Change the emulated delay
	ssh nebula106 "sudo tc qdisc change dev enp1s0f2 root handle 0: netem delay ${d}us"

	sleep 10
done

cat tcp_control2_output/srv_rawop1 | tail -n +19 | head -n 70 | gawk '{print $7}' >> $plotdata_file_nodelay
cat tcp_control2_output/srv_rawop2 | tail -n +19 | head -n 70 | gawk '{print $7}' >> $plotdata_file_delay

# Wait for clients to finish
sleep 15

# Kill the iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done
