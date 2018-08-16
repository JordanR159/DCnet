#!/bin/bash

this_host=`hostname`

if [ "$this_host" != "nebula113" ]
then
	echo "Run this script from nebula113"
	exit
fi

n111_umac=98:98:98:00:00:00
n112_umac=98:98:98:00:00:02
n113_umac=98:98:98:00:00:04

n111_rmac=dc:dc:dc:00:00:00
n112_rmac=dc:dc:dc:00:01:00
n113_rmac=dc:dc:dc:01:00:00

n111_mac=`ssh nebula111 "ifconfig dcnet-srv000" | grep HWaddr | gawk '{print $5}'`
n112_mac=`ssh nebula112 "ifconfig dcnet-srv010" | grep HWaddr | gawk '{print $5}'`
n113_mac=`ifconfig dcnet-srv100 | grep HWaddr | gawk '{print $5}'`

echo "$n111_mac"
echo "$n112_mac"
echo "$n113_mac"

echo "setting ip etc. on 111"
# Set IP address and neighbor entries at nebula111 (dcnet-srv000)
ssh nebula111 "sudo ip link del vxlan1 > /dev/null 2>&1"
ssh nebula111 "sudo ip link set dcnet-srv000 down"
ssh nebula111 "sudo ip link set dcnet-srv000 up"
ssh nebula111 "sudo ifconfig dcnet-srv000 mtu 9000"
ssh nebula111 "sudo ifconfig eth1 mtu 9000"
ssh nebula111 "sudo ip -6 addr add dc90::9090:9000:0/64 dev dcnet-srv000"
ssh nebula111 "sudo ip -6 addr add dc98::d4ae:52c9:a834/64 dev dcnet-srv000"
ssh nebula111 "sudo ip -6 neigh add dev dcnet-srv000 dc90::9090:9000:2 lladdr $n112_mac"
ssh nebula111 "sudo ip -6 neigh add dev dcnet-srv000 dc90::9090:9000:4 lladdr $n113_mac"
ssh nebula111 "sudo ip -6 neigh add dev dcnet-srv000 dc98::d4ae:52c9:ab16 lladdr $n112_umac"
ssh nebula111 "sudo ip -6 neigh add dev dcnet-srv000 dc98::d4ae:52c8:c361 lladdr $n113_umac"
ssh nebula111 "sudo ip link add name vxlan1 type vxlan id 0xdc98 dev dcnet-srv000 remote dc90::9090:9000:4 local dc90::9090:9000:0 dstport 0"
n111_vmac=`ssh nebula111 "ifconfig vxlan1" | grep HWaddr | gawk '{print $5}'`

echo "setting ip etc. on 112"
# Set IP address and neighbor entries at nebula112 (dcnet-srv010)
ssh nebula112 "sudo ip link del vxlan1 > /dev/null 2>&1"
ssh nebula112 "sudo ip link set dcnet-srv010 down"
ssh nebula112 "sudo ip link set dcnet-srv010 up"
ssh nebula112 "sudo ifconfig dcnet-srv010 mtu 9000"
ssh nebula112 "sudo ifconfig eno2 mtu 9000"
ssh nebula112 "sudo ip -6 addr add dc90::9090:9000:2/64 dev dcnet-srv010"
ssh nebula112 "sudo ip -6 addr add dc98::d4ae:52c9:ab16/64 dev dcnet-srv010"
ssh nebula112 "sudo ip -6 neigh add dev dcnet-srv010 dc90::9090:9000:0 lladdr $n111_mac"
ssh nebula112 "sudo ip -6 neigh add dev dcnet-srv010 dc90::9090:9000:4 lladdr $n113_mac"
ssh nebula112 "sudo ip -6 neigh add dev dcnet-srv010 dc98::d4ae:52c9:a834 lladdr $n111_umac"
ssh nebula112 "sudo ip -6 neigh add dev dcnet-srv010 dc98::d4ae:52c8:c361 lladdr $n113_umac"
ssh nebula112 "sudo ip link add name vxlan1 type vxlan id 0xdc99 dev dcnet-srv010 remote dc90::9090:9000:4 local dc90::9090:9000:2 dstport 0"
n112_vmac=`ssh nebula112 "ifconfig vxlan1" | grep HWaddr | gawk '{print $5}'`

echo "setting ip etc. on 113"
# Set IP address and neighbor entries at nebula113 (dcnet-srv100)
sudo ip link del vxlan1 > /dev/null 2>&1
sudo ip link del vxlan2 > /dev/null 2>&1
sudo ip link set dcnet-srv100 down
sudo ip link set dcnet-srv100 up
sudo ifconfig dcnet-srv100 mtu 9000
sudo ifconfig em2 mtu 9000
sudo ip -6 addr add dc90::9090:9000:4/64 dev dcnet-srv100
sudo ip -6 addr add dc98::d4ae:52c8:c361/64 dev dcnet-srv100
sudo ip -6 neigh add dev dcnet-srv100 dc90::9090:9000:0 lladdr $n111_mac
sudo ip -6 neigh add dev dcnet-srv100 dc90::9090:9000:2 lladdr $n112_mac
sudo ip -6 neigh add dev dcnet-srv100 dc98::d4ae:52c9:a834 lladdr $n111_umac
sudo ip -6 neigh add dev dcnet-srv100 dc98::d4ae:52c9:ab16 lladdr $n112_umac
sudo ip link add name vxlan1 type vxlan id 0xdc98 dev dcnet-srv100 remote dc90::9090:9000:0 local dc90::9090:9000:4 dstport 0
n113_vmac1=`ifconfig vxlan1 | grep HWaddr | gawk '{print $5}'`
sudo ip link add name vxlan2 type vxlan id 0xdc99 dev dcnet-srv100 remote dc90::9090:9000:2 local dc90::9090:9000:4 dstport 0
n113_vmac2=`ifconfig vxlan2 | grep HWaddr | gawk '{print $5}'`



ssh nebula111 "sudo ifconfig vxlan1 mtu 8930; sudo ip -6 addr add dc91::9191:9100:0/64 dev vxlan1; sudo ip -6 neigh add dc91::9191:9100:4 lladdr $n113_vmac1 dev vxlan1; sudo ip link set vxlan1 up; sudo tc qdisc add dev vxlan1 root handle 0: pfifo limit 1000"
ssh nebula112 "sudo ifconfig vxlan1 mtu 8930; sudo ip -6 addr add dc92::9292:9200:2/64 dev vxlan1; sudo ip -6 neigh add dc92::9292:9200:4 lladdr $n113_vmac2 dev vxlan1; sudo ip link set vxlan1 up; sudo tc qdisc add dev vxlan1 root handle 0: pfifo limit 1000"
sudo ifconfig vxlan1 mtu 8930; sudo ip -6 addr add dc91::9191:9100:4/64 dev vxlan1; sudo ip -6 neigh add dc91::9191:9100:0 lladdr $n111_vmac dev vxlan1; sudo ip link set vxlan1 up; sudo tc qdisc add dev vxlan1 root handle 0: pfifo limit 1000
sudo ifconfig vxlan2 mtu 8930; sudo ip -6 addr add dc92::9292:9200:4/64 dev vxlan2; sudo ip -6 neigh add dc92::9292:9200:2 lladdr $n112_vmac dev vxlan2; sudo ip link set vxlan2 up; sudo tc qdisc add dev vxlan2 root handle 0: pfifo limit 1000

# Rules in nebula111 (dcnet-srv000)
ssh nebula111 "sudo ovs-ofctl del-flows dcnet-srv000 -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=2001,eth_dst=$n111_mac,actions=output:local -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=2001,ipv6,dl_dst=dc:dc:dc:00:00:00/ff:ff:ff:00:00:00,actions=move:NXM_NX_IPV6_DST[0..47]-\>NXM_OF_ETH_DST[],resubmit\(,0\) -O openflow13"
ssh nebula111 "sudo ovs-ofctl add-flow dcnet-srv000 priority=2000,ipv6,actions=output:1 -O openflow13"

# Rules in nebula112 (dcnet-srv010)
ssh nebula112 "sudo ovs-ofctl del-flows dcnet-srv010 -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=2001,eth_dst=$n112_mac,actions=output:local -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=2001,ipv6,dl_dst=dc:dc:dc:00:00:00/ff:ff:ff:00:00:00,actions=move:NXM_NX_IPV6_DST[0..47]-\>NXM_OF_ETH_DST[],resubmit\(,0\) -O openflow13"
ssh nebula112 "sudo ovs-ofctl add-flow dcnet-srv010 priority=2000,ipv6,actions=output:1 -O openflow13"

# Rules in nebula113 (dcnet-srv100)
sudo ovs-ofctl del-flows dcnet-srv100 -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=2001,eth_dst=$n113_mac,actions=output:local -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=2001,ipv6,dl_dst=dc:dc:dc:00:00:00/ff:ff:ff:00:00:00,actions=move:NXM_NX_IPV6_DST[0..47]-\>NXM_OF_ETH_DST[],resubmit\(,0\) -O openflow13
sudo ovs-ofctl add-flow dcnet-srv100 priority=2000,ipv6,actions=output:1 -O openflow13

# Rules in nebula105 (dcnet-edge00)
ssh nebula105 "sudo ovs-ofctl del-flows dcnet-edge00 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n111_mac,actions=output:1 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n112_mac,actions=output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n113_mac,actions=output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n112_umac,actions=set_field:$n112_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula105 "sudo ovs-ofctl add-flow dcnet-edge00 priority=2001,eth_dst=$n113_umac,actions=set_field:$n113_rmac-\>eth_dst,output:3 -O openflow13"

# Rules in nebula106 (dcnet-edge01)
ssh nebula106 "sudo ovs-ofctl del-flows dcnet-edge01 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n111_mac,actions=output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n112_mac,actions=output:1 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n113_mac,actions=output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n112_rmac,actions=output:1 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n111_umac,actions=set_field:$n111_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula106 "sudo ovs-ofctl add-flow dcnet-edge01 priority=2001,eth_dst=$n113_umac,actions=set_field:$n113_rmac-\>eth_dst,output:3 -O openflow13"

# Rules in nebula103 (dcnet-aggr00)
ssh nebula103 "sudo ovs-ofctl del-flows dcnet-aggr00 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n111_mac,actions=output:1 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n112_mac,actions=output:2 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n113_mac,actions=output:3 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n112_rmac,actions=output:2 -O openflow13"
ssh nebula103 "sudo ovs-ofctl add-flow dcnet-aggr00 priority=2001,eth_dst=$n113_rmac,actions=output:3 -O openflow13"

# Rules in nebula101 (dcnet-core0)
ssh nebula101 "sudo ovs-ofctl del-flows dcnet-core0 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n111_mac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n112_mac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n113_mac,actions=output:2 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n111_rmac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n112_rmac,actions=output:1 -O openflow13"
ssh nebula101 "sudo ovs-ofctl add-flow dcnet-core0 priority=2001,eth_dst=$n113_rmac,actions=output:2 -O openflow13"

# Rules in nebula107 (dcnet-aggr10)
ssh nebula107 "sudo ovs-ofctl del-flows dcnet-aggr10 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n111_mac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n112_mac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n113_mac,actions=output:1 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n111_rmac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n112_rmac,actions=output:3 -O openflow13"
ssh nebula107 "sudo ovs-ofctl add-flow dcnet-aggr10 priority=2001,eth_dst=$n113_rmac,actions=output:1 -O openflow13"

# Rules in nebula109 (dcnet-edge10)
ssh nebula109 "sudo ovs-ofctl del-flows dcnet-edge10 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n111_mac,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n112_mac,actions=output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n113_mac,actions=output:1 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n113_rmac,actions=output:1 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n111_umac,actions=set_field:$n111_rmac-\>eth_dst,output:3 -O openflow13"
ssh nebula109 "sudo ovs-ofctl add-flow dcnet-edge10 priority=2001,eth_dst=$n112_umac,actions=set_field:$n112_rmac-\>eth_dst,output:3 -O openflow13"
