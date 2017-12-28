#!/bin/bash

# Remove the previous output and create a new directory
rm -rf tcp_ovs2_output/
mkdir -p tcp_ovs2_output

# Kill any previously running iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done

# Start the iperf3 servers at two different ports
echo "Starting the servers..."
iperf3 -s -B dc98::9898:9800:4 --logfile tcp_ovs2_output/srv_rawop1 -D
iperf3 -s -B dc99::9999:9900:4 --logfile tcp_ovs2_output/srv_rawop2 -D

plotdata_file_norewriting="tcp_ovs2_output/plotdata_norewriting"
plotdata_file_rewriting="tcp_ovs2_output/plotdata_rewriting"
echo "#no-rewriting" > $plotdata_file_norewriting
echo "#with-rewriting" > $plotdata_file_rewriting

# Start the clients
echo "Starting the clients..."
ssh -f nebula111 "iperf3 -c dc98::9898:9800:4 -O 10 -t 25 > /dev/null"
ssh -f nebula112 "iperf3 -c dc99::9999:9900:4 -O 10 -t 25 > /dev/null"

sleep 40

cat tcp_ovs2_output/srv_rawop1 | tail -n +19 | head -n 20 | gawk '{print $7}' >> $plotdata_file_norewriting
cat tcp_ovs2_output/srv_rawop2 | tail -n +19 | head -n 20 | gawk '{print $7}' >> $plotdata_file_rewriting

# Kill the iperf3 servers
for p in $(ps -aef | grep rajas | grep "iperf3 -s" | grep -v grep | gawk '{print $2}')
do
	kill -9 $p
done
