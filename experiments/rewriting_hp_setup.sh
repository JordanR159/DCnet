#!/bin/bash

n101_eth=`ssh nebula101 "ifconfig eth1" | grep -i hwaddr | gawk '{print $5}'`
n102_eth=`ssh nebula102 "ifconfig eth1" | grep -i hwaddr | gawk '{print $5}'`
n101_r_eth='98:98:98:00:00:d1'
n102_r_eth='98:98:98:00:00:d2'

hp113='tcp:10.10.0.13:8833'
hp111='tcp:10.10.0.11:8833'
hp109='tcp:10.10.0.9:8833'
hp108='tcp:10.10.0.8:8833'
hp107='tcp:10.10.0.7:8833'

# Connection
# n101 <--> 23, hp113, 24 <--> 23, hp111, 24 <--> 23, hp109, 24 <--> 41, hp108, 42 <--> 41, hp107, 42 <--> n102

# Rules in hp113
# n101 direct
# n102 direct, rewrite
echo "Adding rules to hp113"
sudo ovs-ofctl del-flows $hp113 table=100 -O openflow13
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n101_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n102_eth,actions=output:24 -O openflow13
sudo ovs-ofctl add-flow $hp113 table=100,priority=1001,eth_dst=$n102_r_eth,actions=set_field:${n102_eth}-\>eth_dst,output:24 -O openflow13

# Rules in hp111
# n101 direct
# n102 direct
echo "Adding rules to hp111"
sudo ovs-ofctl del-flows $hp111 table=100 -O openflow13
sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n101_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp111 table=100,priority=1001,eth_dst=$n102_eth,actions=output:24 -O openflow13

# Rules in hp109
# n101 direct
# n102 direct
echo "Adding rules to hp109"
sudo ovs-ofctl del-flows $hp109 table=100 -O openflow13
sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n101_eth,actions=output:23 -O openflow13
sudo ovs-ofctl add-flow $hp109 table=100,priority=1001,eth_dst=$n102_eth,actions=output:24 -O openflow13

# Rules in hp108
# n101 direct
# n102 direct
echo "Adding rules to hp108"
sudo ovs-ofctl del-flows $hp108 table=100 -O openflow13
sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n101_eth,actions=output:41 -O openflow13
sudo ovs-ofctl add-flow $hp108 table=100,priority=1001,eth_dst=$n102_eth,actions=output:42 -O openflow13

# Rules in hp107
# n101 direct
# n102 direct
echo "Adding rules to hp107"
sudo ovs-ofctl del-flows $hp107 table=100 -O openflow13
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n101_eth,actions=output:41 -O openflow13
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n101_r_eth,actions=set_field:${n101_eth}-\>eth_dst,output:41 -O openflow13
sudo ovs-ofctl add-flow $hp107 table=100,priority=1001,eth_dst=$n102_eth,actions=output:42 -O openflow13

# Set IP addresses and neighbor cache entries in n101
ssh nebula101 "sudo ip link set eth1 down"
ssh nebula101 "sudo ip link set eth1 up"
ssh nebula101 "sudo ip -6 addr add dc99::9898:9800:d1/64 dev eth1"
ssh nebula101 "sudo ip -6 addr add dc98::9898:9800:d1/64 dev eth1"
ssh nebula101 "sudo ip -6 neigh add dc99::9898:9800:d2 lladdr ${n102_eth} dev eth1"
ssh nebula101 "sudo ip -6 neigh add dc98::9898:9800:d2 lladdr ${n102_r_eth} dev eth1"

# Set IP addresses and neighbor cache entries in n102
ssh nebula102 "sudo ip link set eth1 down"
ssh nebula102 "sudo ip link set eth1 up"
ssh nebula102 "sudo ip -6 addr add dc99::9898:9800:d2/64 dev eth1"
ssh nebula102 "sudo ip -6 addr add dc98::9898:9800:d2/64 dev eth1"
ssh nebula102 "sudo ip -6 neigh add dc99::9898:9800:d1 lladdr ${n101_eth} dev eth1"
ssh nebula102 "sudo ip -6 neigh add dc98::9898:9800:d1 lladdr ${n101_r_eth} dev eth1"
