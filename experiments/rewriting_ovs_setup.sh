#!/bin/bash

# To be executed from nebula113

n111_eth=`ssh nebula111 "ifconfig eth1" | grep -i hwaddr | gawk '{print $5}'`
n112_eth=`ssh nebula112 "ifconfig eno2" | grep -i hwaddr | gawk '{print $5}'`
n113_eth=`ifconfig em2 | grep -i hwaddr | gawk '{print $5}'`

n111_r_eth=98:98:98:00:00:00
n112_r_eth=98:98:98:00:00:02
n113_r_eth=98:98:98:00:00:04

# Rules for nebula105 (dcnet-edge00)
# n111 direct
# n113 direct, rewriting
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n111_eth,actions=output:1 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n113_eth,actions=output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n113_r_eth,actions=set_field:$n113_eth-\>eth_dst,output:3 -O openflow13"

# Rules for nebula106 (dcnet-edge01)
# n112 direct
# n113 direct, rewriting
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n112_eth,actions=output:1 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n113_eth,actions=output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n113_r_eth,actions=set_field:$n113_eth-\>eth_dst,output:3 -O openflow13"

# Rules for nebula103 (dcnet-aggr00)
# n111 direct
# n112 direct
# n113 direct
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n111_eth,actions=output:1 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n112_eth,actions=output:2 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n113_eth,actions=output:3 -O openflow13"

# Rules for nebula101 (dcnet-core0)
# n111 direct
# n112 direct
# n113 direct
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n111_eth,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n112_eth,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n113_eth,actions=output:2 -O openflow13"

# Rules for nebula107 (dcnet-aggr10)
# n111 direct
# n112 direct
# n113 direct
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n111_eth,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n112_eth,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n113_eth,actions=output:1 -O openflow13"

# Rules for nebula109 (dcnet-edge10)
# n111 direct, rewriting
# n112 direct, rewriting
# n113 direct
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n111_eth,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n111_r_eth,actions=set_field:$n111_eth-\>eth_dst,output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n112_eth,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n112_r_eth,actions=set_field:$n112_eth-\>eth_dst,output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n113_eth,actions=output:1 -O openflow13"

# Set up IP addresses and neighbor cache entries for nebula111
ssh nebula111 "sudo ip link set eth1 down"
ssh nebula111 "sudo ip link set eth1 up"
ssh nebula111 "sudo ip -6 addr add dc98::9898:9800:0/64 dev eth1"
ssh nebula111 "sudo ip -6 addr add dc99::9898:9800:0/64 dev eth1"
ssh nebula111 "sudo ip -6 neigh add dc98::9898:9800:4 lladdr $n113_r_eth dev eth1"
ssh nebula111 "sudo ip -6 neigh add dc99::9898:9800:4 lladdr $n113_eth dev eth1"

# Set up IP addresses and neighbor cache entries for nebula112
ssh nebula112 "sudo ip link set eno2 down"
ssh nebula112 "sudo ip link set eno2 up"
ssh nebula112 "sudo ip -6 addr add dc98::9898:9800:2/64 dev eno2"
ssh nebula112 "sudo ip -6 addr add dc99::9898:9800:2/64 dev eno2"
ssh nebula112 "sudo ip -6 neigh add dc98::9898:9800:4 lladdr $n113_r_eth dev eno2"
ssh nebula112 "sudo ip -6 neigh add dc99::9898:9800:4 lladdr $n113_eth dev eno2"

# Set up IP addresses and neighbor cache entries for nebula112
sudo ip link set em2 down
sudo ip link set em2 up
sudo ip -6 addr add dc98::9898:9800:4/64 dev em2
sudo ip -6 addr add dc99::9898:9800:4/64 dev em2
sudo ip -6 neigh add dc98::9898:9800:0 lladdr $n111_r_eth dev em2
sudo ip -6 neigh add dc99::9898:9800:0 lladdr $n111_eth dev em2
sudo ip -6 neigh add dc98::9898:9800:2 lladdr $n112_r_eth dev em2
sudo ip -6 neigh add dc99::9898:9800:2 lladdr $n112_eth dev em2
