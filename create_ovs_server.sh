#!/bin/bash

this_host=`hostname`

if [ $this_host = 'nebula111' ]
then
	sudo ovs-vsctl del-br dcnet-srv000
	sudo ovs-vsctl add-br dcnet-srv000
	sudo ovs-vsctl set bridge dcnet-srv000 protocols=OpenFlow13
	sudo ovs-vsctl set bridge dcnet-srv000 other-config:datapath-id=0000000000000001
	sudo ovs-vsctl add-port dcnet-srv000 eth1
	sudo ovs-vsctl add-port dcnet-srv000 hyp-conn
	sudo ovs-vsctl set-controller dcnet-srv000 tcp:127.0.0.1:6633
elif [ $this_host = 'nebula112' ]
then
	sudo ovs-vsctl del-br dcnet-srv010
	sudo ovs-vsctl add-br dcnet-srv010
	sudo ovs-vsctl set bridge dcnet-srv010 protocols=OpenFlow13
	sudo ovs-vsctl set bridge dcnet-srv010 other-config:datapath-id=0000000000000003
	sudo ovs-vsctl add-port dcnet-srv000 eno2
	sudo ovs-vsctl add-port dcnet-srv000 hyp-conn
	sudo ovs-vsctl set-controller dcnet-srv010 tcp:127.0.0.1:6633
elif [ $this_host = 'nebula113' ]
then
	sudo ovs-vsctl del-br dcnet-srv100
	sudo ovs-vsctl add-br dcnet-srv100
	sudo ovs-vsctl set bridge dcnet-srv100 protocols=OpenFlow13
	sudo ovs-vsctl set bridge dcnet-srv100 other-config:datapath-id=0000000000000005
	sudo ovs-vsctl add-port dcnet-srv100 em2
	sudo ovs-vsctl add-port dcnet-srv100 hyp-conn
	sudo ovs-vsctl set-controller dcnet-srv100 tcp:127.0.0.1:6633
fi
