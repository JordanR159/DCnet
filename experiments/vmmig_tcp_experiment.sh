#!/bin/bash

# Remove previous output and create new directory
rm -rf vmmig_tcp_output
mkdir -p vmmig_tcp_output

# Starting UID
uid=8

# Get the starting UID from command line if provided
if [ $# -gt 0 ]
then
	uid=$1
fi

echo "Starting UID $uid"

uid_hex=`printf "%x" $uid`

# Create a VM
curl -X PUT -d '{"server":"dcnet-srv000"}' http://nebula102:8080/DCnet/create-vm

# Start iperf server on the VM
expect -c "spawn ssh -o \"StrictHostKeyChecking no\" tc@dc98::9898:9800:${uid_hex} iperf3 -s -B dc98::9898:9800:${uid_hex} -D; expect \"password:\"; send \"DCnet98\!\n\"; expect eof"
sleep 2

# Start the iperf client locally
iperf3 -c dc98::9898:9800:${uid_hex} -O 10 -t 15 -i 0.25 > vmmig_tcp_output/rawop1 &

sleep 14

# Migrate the VM with no optimization
curl -X PUT -d "{ \"uid\":${uid}, \"dst\":\"dcnet-srv100\", \"optimize\":0, \"n_tor\":5000 }" http://nebula102:8080/DCnet/migrate-vm

sleep 20

# Delete the VM
curl -X PUT -d "{ \"uid\":${uid} }" http://nebula102:8080/DCnet/delete-vm

time=0.0
for t in $(cat vmmig_tcp_output/rawop1 | tail -n +52 | head -n 40 | gawk '{print $7}')
do
	echo -e "${time}\t${t}" >> vmmig_tcp_output/plotdata_noopt
	time=`echo "${time} + 0.25" | bc -l`
done

uid=`echo "$uid + 1" | bc`
uid_hex=`printf "%x" $uid`

# Create a VM
curl -X PUT -d '{"server":"dcnet-srv000"}' http://nebula102:8080/DCnet/create-vm

# Start iperf server on the VM
expect -c "spawn ssh -o \"StrictHostKeyChecking no\" tc@dc98::9898:9800:${uid_hex} iperf3 -s -B dc98::9898:9800:${uid_hex} -D; expect \"password:\"; send \"DCnet98\!\n\"; expect eof"
sleep 2

# Start the iperf client locally
iperf3 -c dc98::9898:9800:${uid_hex} -O 10 -t 15 -i 0.25 > vmmig_tcp_output/rawop2 &

sleep 14

# Migrate the VM with optimization
curl -X PUT -d "{ \"uid\":${uid}, \"dst\":\"dcnet-srv100\", \"optimize\":1, \"n_tor\":5000 }" http://nebula102:8080/DCnet/migrate-vm

sleep 20

# Delete the VM
curl -X PUT -d "{ \"uid\":${uid} }" http://nebula102:8080/DCnet/delete-vm

time=0.0
for t in $(cat vmmig_tcp_output/rawop2 | tail -n +52 | head -n 40 | gawk '{print $7}')
do
	echo -e "${time}\t${t}" >> vmmig_tcp_output/plotdata_opt
	time=`echo "${time} + 0.25" | bc -l`
done

