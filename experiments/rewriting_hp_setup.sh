#!/bin/bash

n108_eth=`ssh nebula108 "ifconfig p1p4" | grep -i hwaddr | gawk '{print $5}'`
n107_eth=`ssh nebula107 "ifconfig enp1s0f3" | grep -i hwaddr | gawk '{print $5}'`
n108_r_eth='98:98:98:00:00:18'
n107_r_eth='98:98:98:00:00:17'

hp113='tcp:10.10.0.13:8833'
hp111='tcp:10.10.0.11:8833'
hp109='tcp:10.10.0.9:8833'
hp108='tcp:10.10.0.8:8833'
hp107='tcp:10.10.0.7:8833'

# Connection
# n108 <--> 23, hp113, 24 <--> 23, hp111, 24 <--> 23, hp109, 24 <--> 41, hp108, 42 <--> 41, hp107, 42 <--> n107

# Rules in hp113
# n108 direct
# n107 direct, rewrite
echo "Adding rules to hp113"
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n108_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n107_eth,actions=output:24 -O openflow13
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n107_r_eth,actions=set_field:${n107_eth}-\>eth_dst,output:24 -O openflow13

# Rules in hp111
# n108 direct
# n107 direct
echo "Adding rules to hp111"
sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n108_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n107_eth,actions=output:24 -O openflow13

# Rules in hp109
# n108 direct
# n107 direct
echo "Adding rules to hp109"
sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n108_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n107_eth,actions=output:24 -O openflow13

# Rules in hp108
# n108 direct
# n107 direct
echo "Adding rules to hp108"
sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n108_eth,actions=output:41 -O openflow13
sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n107_eth,actions=output:42 -O openflow13

# Rules in hp107
# n108 direct
# n107 direct
echo "Adding rules to hp107"
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n108_eth,actions=output:41 -O openflow13
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n108_r_eth,actions=set_field:${n108_eth}-\>eth_dst,output:41 -O openflow13
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n107_eth,actions=output:42 -O openflow13

# Set IP addresses and neighbor cache entries in n108
ssh nebula108 "sudo ip link set p1p4 down"
ssh nebula108 "sudo ip link set p1p4 up"
ssh nebula108 "sudo ip -6 addr add dc99::9898:9800:108/64 dev p1p4"
ssh nebula108 "sudo ip -6 addr add dc98::9898:9800:108/64 dev p1p4"
ssh nebula108 "sudo ip -6 neigh add dc99::9898:9800:107 lladdr ${n107_eth} dev p1p4"
ssh nebula108 "sudo ip -6 neigh add dc98::9898:9800:107 lladdr ${n107_r_eth} dev p1p4"

# Set IP addresses and neighbor cache entries in n107
ssh nebula107 "sudo ip link set enp1s0f3 down"
ssh nebula107 "sudo ip link set enp1s0f3 up"
ssh nebula107 "sudo ip -6 addr add dc99::9898:9800:107/64 dev enp1s0f3"
ssh nebula107 "sudo ip -6 addr add dc98::9898:9800:107/64 dev enp1s0f3"
ssh nebula107 "sudo ip -6 neigh add dc99::9898:9800:108 lladdr ${n108_eth} dev enp1s0f3"
ssh nebula107 "sudo ip -6 neigh add dc98::9898:9800:108 lladdr ${n108_r_eth} dev enp1s0f3"
