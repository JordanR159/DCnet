from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import RemoteController, Node, Host, OVSKernelSwitch
from mininet.link import TCLink

from mininet.link import TCLink
from argparse import ArgumentParser
import traceback
import random
import time

# Function to parse the command line arguments
def parseOptions():
	leaf = 4
	spine = 2
	pod = 2
	ss_ratio = 2
	fanout = 3
	dc = 2
	test = False

	parser = ArgumentParser("Create a folded Clos network topology")

	# Add arguments to the parser for leaf, spine, pod, super spine, and fanout options
	parser.add_argument("--leaf", type = int, help = "Number of leaf switches per pod")
	parser.add_argument("--spine", type = int, help = "Number of spine switches per pod")
	parser.add_argument("--pod", type = int, help = "Number of pods per data center")
	parser.add_argument("--ratio", type = int
						, help = "Number of super spine switches per spine switch")
	parser.add_argument("--fanout", type = int, help = "Number of hosts per leaf switch")
	parser.add_argument("--dc", type = int, help = "Number of data centers")
	parser.add_argument("--test", help = "Enable automatic testing")

	args = parser.parse_args()

	# Change the values if passed on command line
	if args.leaf:
		leaf = args.leaf
	if args.spine:
		spine = args.spine
	if args.pod:
		pod = args.pod
	if args.ratio:
		ss_ratio = args.ratio
	if args.pod:
		fanout = args.fanout
	if args.dc:
		dc = args.dc
	if args.test:
		test = True

	# return the values
	return leaf, spine, pod, ss_ratio, fanout, dc, test

def createTraffic(shuffle, host):
	h = 0
	while h < len(shuffle):
		server = shuffle[h]
		client = shuffle[h + 1]
		if server.name == host.name or client.name == host.name:
			h += 2
			continue
		server.cmd("iperf3 -s -1 &")
		client.cmd("iperf3 -t 25 -c " + server.IP() + " &")
		h += 2

def runPingTests(net, pods, dcs, with_load):
	host = net.hosts[0]
	if with_load is True:
		ping_out = open("ping_test_with_load.out", "w+")
	else:
		ping_out = open("ping_test_no_load.out", "w+")
	shuffle = list(net.hosts)
	random.shuffle(shuffle)
	print("Ping Test 1")
	if with_load is True:
		createTraffic(shuffle, host)
	ping_out.write("\n--- Ping Test 1 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[1].IP()))
	print("Ping Test 2")
	ping_out.write("\n--- Ping Test 2 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[1].IP()))
	time.sleep(10)
	print("Ping Test 3")
	if with_load is True:
		createTraffic(shuffle, host)
	ping_out.write("\n--- Ping Test 3 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[len(net.hosts)/(dcs*pods)-1].IP()))
	print("Ping Test 4")
	ping_out.write("\n--- Ping Test 4 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[len(net.hosts)/(dcs*pods)-1].IP()))
	time.sleep(10)
	print("Ping Test 5")
	if with_load is True:
		createTraffic(shuffle, host)
	ping_out.write("\n--- Ping Test 5 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[len(net.hosts) / dcs - 1].IP()))
	print("Ping Test 6")
	ping_out.write("\n--- Ping Test 6 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[len(net.hosts) / dcs - 1].IP()))
	time.sleep(10)
	print("Ping Test 7")
	if with_load is True:
		createTraffic(shuffle, host)
	ping_out.write("\n--- Ping Test 7 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[-1].IP()))
	print("Ping Test 8")
	ping_out.write("\n--- Ping Test 8 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[-1].IP()))
	time.sleep(10)

def runTCPTests(net, pods, dcs, with_load):
	client = net.hosts[0]
	if with_load is True:
		tcp_out = open("tcp_test_with_load.out", "w+")
	else:
		tcp_out = open("tcp_test_no_load.out", "w+")
	shuffle = list(net.hosts)
	random.shuffle(shuffle)
	print("TCP Test 1")
	if with_load is True:
		createTraffic(shuffle, client)
	server = net.hosts[1]
	server.cmd("iperf3 -s -1 -p 5250 &")
	tcp_out.write("\n--- TCP Test 1: ")
	tcp_out.write(client.name + " sending to " + server.name + " ---\n")
	tcp_out.write(client.cmd("iperf3 -t 20 -p 5250 -c " + server.IP()))
	time.sleep(10)
	print("TCP Test 2")
	if with_load is True:
		createTraffic(shuffle, client)
	server = net.hosts[len(net.hosts)/(dcs * pods) - 1]
	server.cmd("iperf3 -s -1 -p 5250 &")
	tcp_out.write("\n--- TCP Test 2: ")
	tcp_out.write(client.name + " sending to " + server.name + " ---\n")
	tcp_out.write(client.cmd("iperf3 -t 20 -p 5250 -c " + server.IP()))
	time.sleep(10)
	print("TCP Test 3")
	if with_load is True:
		createTraffic(shuffle, client)
	server = net.hosts[len(net.hosts)/dcs - 1]
	server.cmd("iperf3 -s -1 -p 5250 &")
	tcp_out.write("\n--- TCP Test 3: ")
	tcp_out.write(client.name + " sending to " + server.name + " ---\n")
	tcp_out.write(client.cmd("iperf3 -t 20 -p 5250 -c " + server.IP()))
	time.sleep(10)
	print("TCP Test 4")
	if with_load is True:
		createTraffic(shuffle, client)
	server = net.hosts[len(net.hosts) - 1]
	server.cmd("iperf3 -s -1 -p 5250 &")
	tcp_out.write("\n--- TCP Test 4: ")
	tcp_out.write(client.name + " sending to " + server.name + " ---\n")
	tcp_out.write(client.cmd("iperf3 -t 20 -p 5250 -c " + server.IP()))
	time.sleep(10)


# Class defining a Folded Clos topology using super spines
class FoldedClos(Topo):
	def __init__(self, leaf, spine, pod, ss_ratio, fanout, dc):
		"Create Leaf and Spine Topo."

		Topo.__init__(self)

		# Simple counter for assigning host names
		host_count = 1
		switch_count = 1;

		# Counter with adjustable increments for switch names. Choose
		# increment and initial values to easily identify switch types
		increment = 16
		leaf_count = 10 + increment
		spine_count = 11 + increment
		ss_count = 12 + increment
		dc_count = 13 + increment

		# Configuration file for topology that can be used by SDN controller
		top_config = open("top_config.csv", "w+")
		top_config.write("dc_count,dc_radix_down,ss_radix_down,")
		top_config.write("sp_radix_up,sp_radix_down,lf_radix_up,lf_radix_down\n")
		top_config.write(str(dc) + "," + str(spine * ss_ratio) + ",")
		top_config.write(str(pod) + "," + str(ss_ratio) + ",")
		top_config.write(str(leaf) + "," + str(spine) + "," + str(fanout) + "\n")

		# Configuration file for switches that can be used by SDN controller
		switch_config = open("switch_config.csv", "w+")
		switch_config.write("id,name,level,dc,pod,leaf\n")
		
		# Configuration file for hosts that can be used by SDN controller
		host_config = open("host_config.csv", "w+")
		host_config.write("ip,name,leaf,port,rmac\n")
		
		dc_switches = []
		ss_switches = []
		leaf_switches = []

		for d in range(dc):
			dc_name = "d" + str(dc_count)
			ip_addr = "10.0.1.1" + format(switch_count, "02d") + "/24"
			self.addSwitch(dc_name, ip = ip_addr)
			switch_count += 1;
			dc_switches.append(dc_name)
			switch_config.write(format(dc_count, "x") + "," + dc_name + ",0," + str(d) + ",-1,-1\n")
			dc_count += increment

			# Create super spines
			for ss in range(ss_ratio * spine):
				ss_name = "u" + str(ss_count)
				ip_addr = "10.0.1.1" + format(switch_count, "02d") + "/24"
				self.addSwitch(ss_name, ip = ip_addr)
				switch_count += 1;
				ss_switches.append(ss_name)
				switch_config.write(format(ss_count, "x") + "," + ss_name + ",1," + str(d) + ",-1,-1\n")
				ss_count += increment

			# Create a group of leaf and spine switches for every pod
			for p in range(pod):

				# Create leaves and hosts for each leaf
				for l in range(leaf):
					leaf_name = "l" + str(leaf_count)
					ip_addr = "10.0.1.1" + format(switch_count, "02d") + "/24"
					self.addSwitch(leaf_name, ip = ip_addr)
					switch_count += 1;
					leaf_switches.append(leaf_name)
					switch_config.write(format(leaf_count, "x") + "," + leaf_name + ",3," + str(d) + ",")
					switch_config.write(str(p) + "," + str(l) + "\n")
					leaf_count += increment
					
					# Create hosts, designated by letter h, and link to leaf
					for h in range(fanout):
						host_name = "h" + str(host_count)

						# Construct host IPv4 address, first 8 bits are reserved,
						# last 24 bits uniquely identify a host
						ip_addr = "10.0.1." + str(host_count & 0xFF)
	
						# Construct host UID MAC address, first 24 bits are reserved,
						# last 24 bits uniquely identify a host
						mac_addr = "dc:dc:dc:" + format((host_count >> 16) & 0xFF, "02x")
						mac_addr += ":" + format((host_count >> 8) & 0xFF, "02x")
						mac_addr += ":" + format(host_count & 0xFF, "02x")
	
						# Construct host RMAC address based on dc, pod, leaf, and host
						# First 2 bits are type (unused), next 10 are the data center id,
						# next 12 are pod the number, next 12 are the leaf number, and
						# last 12 are the host number
						rmac_addr = format((d >> 4) & 0x3F, "02x") + ":"
						rmac_addr += format(d & 0xF, "01x")
						rmac_addr += format((p >> 8) & 0xF, "01x") + ":"
						rmac_addr += format(p & 0xFF, "02x") + ":"
						rmac_addr += format((l >> 4) & 0xFF, "02x") + ":"
						rmac_addr += format(l & 0xF, "01x")
						rmac_addr += format((h >> 8)& 0xF, "01x") + ":"
						rmac_addr += format(h & 0xFF, "02x")
	
						self.addHost(host_name, ip = ip_addr + "/24", mac = mac_addr)
						host_config.write(ip_addr + "," + host_name + "," + leaf_name)
						host_config.write("," + str(h) + "," + rmac_addr + "," + mac_addr + "\n")
						host_count += 1
						self.addLink(leaf_name, host_name, cls = TCLink, bw = 10, delay = "0.1ms")
						#self.addLink(leaf_name, host_name)
	
				# Create spines and link to super spines and leaves
				for s in range(spine):
					spine_name = "s" + str(spine_count)
					ip_addr = "10.0.1.1" + format(switch_count, "02d") + "/24"
					self.addSwitch(spine_name, ip = ip_addr)
					switch_count += 1;
					switch_config.write(format(spine_count, "x") + "," + spine_name + ",2," + str(d))
					switch_config.write("," + str(p) + ",-1\n")
					spine_count += increment
					for l in range(leaf):
						self.addLink(spine_name, leaf_switches[l + p*leaf + d*pod*leaf],
										cls = TCLink, bw = 40, delay = "0.1ms")
						#self.addLink(spine_name, leaf_switches[l + p*leaf + d*pod*leaf])
					for ss in range(ss_ratio):
						self.addLink(ss_switches[ss + s*ss_ratio + d*spine*ss_ratio],
										spine_name, cls = TCLink, bw = 40, delay = "0.1ms")
						#self.addLink(ss_switches[ss + s*ss_ratio + d*spine*ss_ratio], spine_name)
			
			# Link super spines to data center router
			for ss in range(ss_ratio * spine):
				ss_name = ss_switches[ss + d*spine*ss_ratio]
				self.addLink(dc_name, ss_name, cls = TCLink, bw = 100, delay = "0.1ms")
				#self.addLink(dc_name, ss_name)
		
		# Let a single high bandwidth, high latency link represent
		# an internet connection between each pair of data centers	
		for d1 in range(dc):
			for d2 in range(d1 + 1, dc):
				self.addLink(dc_switches[d1], dc_switches[d2], cls = TCLink, bw = 1000, delay = "50ms")
				#self.addLink(dc_switches[d1], dc_switches[d2])

if __name__ == "__main__":
	net = None
	try:
		setLogLevel("info")
		leaf, spine, pod, ss_ratio, fanout, dc, test = parseOptions()
		topo = FoldedClos(leaf, spine, pod, ss_ratio, fanout, dc)
		net = Mininet(topo, controller = RemoteController, link = TCLink)
		net.start()

		# Assign IPv6 addresses based on DCnet specifications
		for h in range(len(net.hosts)):
			host = net.hosts[h]
			command = "ifconfig " + host.name + "-eth0 inet6 add dcdc::dc"
			command += format(((h + 1) >> 16) & 0xFF, "02x")
			command += ":" + format((h + 1) & 0xFFFF, "04x") + "/104"
			host.cmd(command)

		# Run ping and TCP tests
		if test is True:
                        time.sleep(30)
			print("*** Running performance tests (no load)")
			runPingTests(net, pod, dc, False)
			runTCPTests(net, pod, dc, False)
		
			print("*** Running performance tests (with load)")
			runPingTests(net, pod, dc, True)
			runTCPTests(net, pod, dc, True)

		CLI(net)
	finally:
		if net is not None:
			net.stop()


topos = {'FoldedClos':
		(lambda leaf, spine, pod, ss_ratio, fanout, dc:
		FoldedClos(leaf, spine, pod, ss_ratio, fanout, dc))}

