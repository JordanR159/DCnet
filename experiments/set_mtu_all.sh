#!/bin/bash

n103_p3=rename91
n103_p4=rename92

echo -e "\n\nnebula103 ports 3,4 : $n103_p3, $n103_p4."
echo "Press ENTER if correct. If incorrect press Ctrl-C and correct the script."
read x

# Default value of MTU
mtu=9000

# Get the value of MTU from command line if available
if [ $# -gt 0 ]
then
	mtu=$1
fi

# Function to set MTU
# arg1 : machine name
# arg2 : interface name
function set_mtu() {
	echo "Setting MTU $mtu for interface $2 on $1"
	ssh $1 "sudo ifconfig $2 mtu $mtu"
}

# nebula101
set_mtu nebula101 eth5
set_mtu nebula101 eth6

# nebula102
set_mtu nebula102 eth7
set_mtu nebula102 eth8

# nebula103
set_mtu nebula103 eth6
set_mtu nebula103 eth7
set_mtu nebula103 $n103_p3
set_mtu nebula103 $n103_p4

# nebula104
for i in `seq 0 3`; do set_mtu nebula104 enp1s0f$i; done

# nebula105
for i in `seq 1 4`; do set_mtu nebula105 p1p$i; done

# nebula106
for i in `seq 0 3`; do set_mtu nebula106 enp1s0f$i; done

# nebula107
for i in `seq 0 3`; do set_mtu nebula107 enp1s0f$i; done

# nebula108
for i in `seq 1 4`; do set_mtu nebula108 p1p$i; done

# nebula109
for i in `seq 1 4`; do set_mtu nebula109 p1p$i; done

# nebula111
set_mtu nebula111 eth1
set_mtu nebula111 hyp
set_mtu nebula111 hyp-conn

# nebula112
set_mtu nebula112 eno2
set_mtu nebula112 hyp
set_mtu nebula112 hyp-conn

# nebula113
sudo ifconfig em2 mtu $mtu
sudo ifconfig hyp mtu $mtu
sudo ifconfig hyp-conn $mtu
