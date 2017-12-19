#!/bin/bash

# To be executed from nebula113

this_host=`hostname`

if [ "$this_host" != "nebula113" ]
then
	echo "Run this script on nebula113 only"
	exit 1
fi

# UID-MACs of servers
n111_umac=98:98:98:00:00:00
n112_umac=98:98:98:00:00:02
n113_umac=98:98:98:00:00:04

# RMACs of servers
n111_rmac=dc:dc:dc:00:00:00
n112_rmac=dc:dc:dc:00:01:00
n113_rmac=dc:dc:dc:01:00:00

# Fake MACs used for rewriting
n111_fmac=99:99:99:00:00:00
n112_fmac=99:99:99:00:00:02
n113_fmac=99:99:99:00:00:04

# Set IP address and neighbor entries at nebula111 (dcnet-srv000)
ssh nebula111 "sudo ip link set hyp down"
ssh nebula111 "sudo ip link set hyp up"
ssh nebula111 "sudo ifconfig hyp mtu 9000"
ssh nebula111 "sudo ifconfig hyp-conn mtu 9000"
ssh nebula111 "sudo ip -6 addr add dc98::9898:9800:0/64 dev hyp"
ssh nebula111 "sudo ip -6 addr add dc99::9999:9900:0/64 dev hyp"
ssh nebula111 "sudo ip -6 neigh add dev hyp dc98::9898:9800:2 lladdr $n112_umac"
ssh nebula111 "sudo ip -6 neigh add dev hyp dc99::9999:9900:2 lladdr $n112_fmac"
ssh nebula111 "sudo ip -6 neigh add dev hyp dc98::9898:9800:4 lladdr $n113_umac"
ssh nebula111 "sudo ip -6 neigh add dev hyp dc99::9999:9900:4 lladdr $n113_fmac"

# Set IP address and neighbor entries at nebula112 (dcnet-srv010)
ssh nebula112 "sudo ip link set hyp down"
ssh nebula112 "sudo ip link set hyp up"
ssh nebula112 "sudo ifconfig hyp mtu 9000"
ssh nebula112 "sudo ifconfig hyp-conn mtu 9000"
ssh nebula112 "sudo ip -6 addr add dc98::9898:9800:2/64 dev hyp"
ssh nebula112 "sudo ip -6 addr add dc99::9999:9900:2/64 dev hyp"
ssh nebula112 "sudo ip -6 neigh add dev hyp dc98::9898:9800:0 lladdr $n111_umac"
ssh nebula112 "sudo ip -6 neigh add dev hyp dc99::9999:9900:0 lladdr $n111_fmac"
ssh nebula112 "sudo ip -6 neigh add dev hyp dc98::9898:9800:4 lladdr $n113_umac"
ssh nebula112 "sudo ip -6 neigh add dev hyp dc99::9999:9900:4 lladdr $n113_fmac"

# Set IP address and neighbor entries at nebula113 (dcnet-srv100)
sudo ip link set hyp down
sudo ip link set hyp up
sudo ifconfig hyp mtu 9000
sudo ifconfig hyp-conn mtu 9000
sudo ip -6 addr add dc98::9898:9800:4/64 dev hyp
sudo ip -6 addr add dc99::9999:9900:4/64 dev hyp
sudo ip -6 neigh add dev hyp dc98::9898:9800:0 lladdr $n111_umac
sudo ip -6 neigh add dev hyp dc99::9999:9900:0 lladdr $n111_fmac
sudo ip -6 neigh add dev hyp dc98::9898:9800:2 lladdr $n112_umac
sudo ip -6 neigh add dev hyp dc99::9999:9900:2 lladdr $n112_fmac

# Rules in nebula111 (dcnet-srv000)
ssh nebula111 "sudo ovs-ofctl del-flows dcnet-srv000 -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=1001,eth_dst=$n111_umac,actions=output:2 -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=1001,ipv6,ipv6_dst=dc99::9999:9900:0,actions=set_field:$n111_umac-\>eth_dst,output:2 -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=1000,ipv6,actions=output:1 -O openflow13"

# Rules in nebula112 (dcnet-srv010)
ssh nebula112 "sudo ovs-ofctl del-flows dcnet-srv010 -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=1001,eth_dst=$n112_umac,actions=output:2 -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=1001,ipv6,ipv6_dst=dc99::9999:9900:2,actions=set_field:$n112_umac-\>eth_dst,output:2 -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=1000,ipv6,actions=output:1 -O openflow13"

# Rules in nebula113 (dcnet-srv100)
sudo ovs-ofctl del-flows dcnet-srv100 -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=1001,eth_dst=$n113_umac,actions=output:2 -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=1001,ipv6,ipv6_dst=dc99::9999:9900:4,actions=set_field:$n113_umac-\>eth_dst,output:2 -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=1000,ipv6,actions=output:1 -O openflow13

echo "nebula105"
# Rules in nebula105 (dcnet-edge00)
# direct rules for umac: n111, n112, n113; rmac: n111
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n111_umac,actions=output:1 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n112_umac,actions=output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n113_umac,actions=output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
# rewriting rules for n112, n113
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n112_fmac,actions=set_field:$n112_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=1001,eth_dst=$n113_fmac,actions=set_field:$n113_rmac-\>eth_dst,output:3 -O openflow13"

echo "nebula106"
# Rules in nebula106 (dcnet-edge01)
# Direct rules for n111, n112, n113
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n111_umac,actions=output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n112_umac,actions=output:1 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n113_umac,actions=output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n112_rmac,actions=output:1 -O openflow13"
# Rewriting rules for n111, n113
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n111_fmac,actions=set_field:$n111_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=1001,eth_dst=$n113_fmac,actions=set_field:$n113_rmac-\>eth_dst,output:3 -O openflow13"

echo "nebula103"
# Rules in nebula103 (dcnet-aggr00)
# direct rules for n111, n112, n113 umac and rmac
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n111_umac,actions=output:1 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n112_umac,actions=output:2 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n113_umac,actions=output:3 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n112_rmac,actions=output:2 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=1001,eth_dst=$n113_rmac,actions=output:3 -O openflow13"

echo "nebula101"
# Rules in nebula101 (dcnet-core0)
# Direct rules for n111, n112, n113
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n111_umac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n112_umac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n113_umac,actions=output:2 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n112_rmac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=1001,eth_dst=$n113_rmac,actions=output:2 -O openflow13"

echo "nebula107"
# Rules in nebula107 (dcnet-aggr10)
# Direct rules for n111, n112, n113
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n111_umac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n112_umac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n113_umac,actions=output:1 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n111_rmac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n112_rmac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=1001,eth_dst=$n113_rmac,actions=output:1 -O openflow13"

echo "nebula109"
# Rules in nebula109 (dcnet-edge10)
# Direct rules for n111, n112, n113
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n111_umac,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n112_umac,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n113_umac,actions=output:1 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n113_rmac,actions=output:1 -O openflow13"
# Rewriting rules for n111, n112
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n111_fmac,actions=set_field:$n111_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=1001,eth_dst=$n112_fmac,actions=set_field:$n112_rmac-\>eth_dst,output:3 -O openflow13"

exit
