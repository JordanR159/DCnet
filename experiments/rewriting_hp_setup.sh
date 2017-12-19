#!/bin/bash

# To be executed from nebula113
host=`hostname`

if [ "$host" != "nebula113" ]
then
	echo "Please execute this script from nebula113"
	exit 1
fi

# UID-MACs of hosts
n101_umac=98:98:98:00:00:d1
n102_umac=98:98:98:00:00:d2

# RMACs of hosts
n101_rmac=dc:dc:dc:00:00:00
n102_rmac=dc:dc:dc:01:00:00

# Fake MACs of hosts
n101_fmac=99:99:99:00:00:d1
n102_fmac=99:99:99:00:00:d2

# Connections to HP switches
hp113='tcp:10.10.0.13:8833'
hp111='tcp:10.10.0.11:8833'
hp109='tcp:10.10.0.9:8833'
hp108='tcp:10.10.0.8:8833'
hp107='tcp:10.10.0.7:8833'

# Set IP addresses and neighbor caches in n101
ssh nebula101 "sudo ip link set hyp down"
ssh nebula101 "sudo ip link set hyp up"
ssh nebula101 "sudo ifconfig hyp mtu 9000"
ssh nebula101 "sudo ip -6 addr add dc98::9898:9800:d1/64 dev hyp"
ssh nebula101 "sudo ip -6 addr add dc99::9999:9900:d1/64 dev hyp"
ssh nebula101 "sudo ip -6 neigh add dc98::9898:9800:d2 dev hyp lladdr $n102_umac"
ssh nebula101 "sudo ip -6 neigh add dc99::9999:9900:d2 dev hyp lladdr $n102_fmac"

# Set IP addresses and neighbor caches in n102
ssh nebula102 "sudo ip link set hyp down"
ssh nebula102 "sudo ip link set hyp up"
ssh nebula102 "sudo ifconfig hyp mtu 9000"
ssh nebula102 "sudo ip -6 addr add dc98::9898:9800:d2/64 dev hyp"
ssh nebula102 "sudo ip -6 addr add dc99::9999:9900:d2/64 dev hyp"
ssh nebula102 "sudo ip -6 neigh add dc98::9898:9800:d1 dev hyp lladdr $n101_umac"
ssh nebula102 "sudo ip -6 neigh add dc99::9999:9900:d1 dev hyp lladdr $n101_fmac"

# Topology
# n101 <--> 23, hp113, 24 <--> 23, hp111, 24 <--> 23, hp109, 24 <--> 41, hp108, 42 <--> 41, hp107, 42 <--> n102

# Rules in dcnet-hp-hvs1
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-hp-hvs1 priority=1001,eth_dst=$n101_umac,actions=output:2 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-hp-hvs1 priority=1001,ipv6,ipv6_dst=dc99::9999:9900:d1,actions=set_field:$n101_umac-\>eth_dst,output:2 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-hp-hvs1 priority=1000,ipv6,actions=output:1 -O openflow13"

# Rules in hp113
# n101 direct UID-MAC and RMAC
# n102 direct, rewrite
echo "Adding rules to hp113"
ssh nebula110 "sudo ovs-ofctl del-flows $hp113 table=100 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n101_umac,actions=output:23 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n102_umac,actions=output:24 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n102_fmac,actions=set_field:$n102_rmac-\>eth_dst,output:24 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n101_rmac,actions=output:23 -O openflow13"

# Rules in hp111
# n101 direct
# n102 direct
echo "Adding rules to hp111"
ssh nebula110 "sudo ovs-ofctl del-flows $hp111 table=100 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n101_umac,actions=output:23 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n102_umac,actions=output:24 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n101_rmac,actions=output:23 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n102_rmac,actions=output:24 -O openflow13"

# Rules in hp109
# n101 direct
# n102 direct
echo "Adding rules to hp109"
ssh nebula110 "sudo ovs-ofctl del-flows $hp109 table=100 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n101_umac,actions=output:23 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n102_umac,actions=output:24 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n101_rmac,actions=output:23 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n102_rmac,actions=output:24 -O openflow13"

# Rules in hp108
# n101 direct
# n102 direct
echo "Adding rules to hp108"
ssh nebula110 "sudo ovs-ofctl del-flows $hp108 table=100 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n101_umac,actions=output:41 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n102_umac,actions=output:42 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n101_rmac,actions=output:41 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n102_rmac,actions=output:42 -O openflow13"

# Rules in hp107
# n101 direct
# n102 direct
echo "Adding rules to hp107"
ssh nebula110 "sudo ovs-ofctl del-flows $hp107 table=100 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n101_umac,actions=output:41 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n102_umac,actions=output:42 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n102_rmac,actions=output:42 -O openflow13"
ssh nebula110 "sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n101_fmac,actions=set_field:$n101_rmac-\>eth_dst,output:41 -O openflow13"

# Rules in dcnet-hp-hvs2
ssh nebula102 "sudo ovs-ofctl del-flows dcnet-hp-hvs2 -O openflow13"
ssh nebula102 "sudo ovs-ofctl add-flow dcnet-hp-hvs2 priority=1001,eth_dst=$n102_umac,actions=output:2 -O openflow13"
ssh nebula102 "sudo ovs-ofctl add-flow dcnet-hp-hvs2 priority=1001,ipv6,ipv6_dst=dc99::9999:9900:d2,actions=set_field:$n102_umac-\>eth_dst,output:2 -O openflow13"
ssh nebula102 "sudo ovs-ofctl add-flow dcnet-hp-hvs2 priority=1000,ipv6,actions=output:1 -O openflow13"
