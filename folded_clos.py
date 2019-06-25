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
	pod = 4
	ss_ratio = 2
	fanout = 3
	dc = 1

	parser = ArgumentParser("Create a folded Clos network topology")

	# Add arguments to the parser for leaf, spine, pod, super spine, and fanout options
	parser.add_argument("--leaf", type = int, help = "Number of leaf switches per pod")
	parser.add_argument("--spine", type = int, help = "Number of spine switches per pod")
	parser.add_argument("--pod", type = int, help = "Number of pods per data center")
	parser.add_argument("--ratio", type = int
						, help = "Number of super spine switches per spine switch")
	parser.add_argument("--fanout", type = int, help = "Number of hosts per leaf switch")
	parser.add_argument("--dc", type = int, help = "Number of data centers")

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

	# return the values
	return leaf, spine, pod, ss_ratio, fanout

def runPingTests(net, pods):
	host = net.hosts[0]
	ping_out = open("ping_test.out", "w+")
	print("Ping Test 1")
	ping_out.write("\n--- Ping Test 1 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[1].IP()))
	print("Ping Test 2")
	ping_out.write("\n--- Ping Test 2 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[1].IP()))
	print("Ping Test 3")
	ping_out.write("\n--- Ping Test 3 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[len(net.hosts) / pods - 1].IP()))
	print("Ping Test 4")
	ping_out.write("\n--- Ping Test 4 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[len(net.hosts) / pods - 1].IP()))
	print("Ping Test 5")
	ping_out.write("\n--- Ping Test 5 Results ---")
	ping_out.write(host.cmd("ping -c 3 " + net.hosts[-1].IP()))
	print("Ping Test 6")
	ping_out.write("\n--- Ping Test 6 Results ---")
	ping_out.write(host.cmd("ping -c 20 " + net.hosts[-1].IP()))

def runTCPTests(net):
	shuffle = list(net.hosts)
	tcp_out = open("tcp_test.out", "w+")
	for i in range(6):
		h = 0
		random.shuffle(shuffle)
		while h < len(shuffle) - 2:
			server = shuffle[h]
			client = shuffle[h + 1]
			server.cmd("iperf3 -s -1 &")
			client.cmd("iperf3 -c " + server.IP() + " &")
			h += 2
		server = shuffle[h]
		client = shuffle[h + 1]
		server.cmd("iperf3 -s -1 &")
		print("TCP Test " + str(i + 1))
		tcp_out.write("\n--- TCP Test " + str(i + 1) + ": ")
		tcp_out.write(client.name + " sending to " + server.name + " ---\n")
		client.cmd("clear")
		tcp_out.write(client.cmd("iperf3 -c " + server.IP()))
		time.sleep(5)

# Class defining a Folded Clos topology using super spines
class FoldedClos(Topo):
	def __init__(self, leaf = 4, spine = 2, pod = 2, ss_ratio = 2, fanout = 3):
		"Create Leaf and Spine Topo."

		Topo.__init__(self)

		ss_switches = []
		leaf_switches = []

		# Simple counter for assigning host names
		host_count = 1

		# Counter with adjustable increments for switch names. Choose
		# increment and initial values to easily identify switch types
		increment = 16
		leaf_count = 10 + increment
		spine_count = 11 + increment
		ss_count = 12 + increment
		dc_count = 13 + increment

		# Configuration file for topology that can be used by SDN controller
		top_config = open("top_config.csv", "w+")
		top_config.write("ss_radix_down,sp_radix_up,sp_radix_down,lf_radix_up,lf_radix_down\n")
		top_config.write(str(pod * ss_ratio) + "," + str(ss_ratio) + ",")
		top_config.write(str(leaf) + "," + str(spine) + "," + str(fanout) + "\n")

		# Configuration file for switches that can be used by SDN controller
		switch_config = open("switch_config.csv", "w+")
		switch_config.write("name,level,pod,leaf,ip\n")
		
		# Configuration file for hosts that can be used by SDN controller
		host_config = open("host_config.csv", "w+")
		host_config.write("name,leaf,port,rmac,ip\n")

		# Create super spines, designated by letter u
		for ss in range(ss_ratio * spine):
			ss_name = "u" + str(ss_count)
			self.addSwitch(ss_name)
			ss_switches.append(ss_name)
			switch_config.write(ss_name + ",0,N/A,N/A\n")
			ss_count += increment

		# Create a group of leaf and spine switches for every pod
		for p in range(pod):

			# Create leaves, designated by letter l, and hosts for each leaf
			for l in range(leaf):
				leaf_name = "l" + str(leaf_count)
				self.addSwitch(leaf_name)
				leaf_switches.append(leaf_name)
				switch_config.write(leaf_name + ",2," + str(p) + "," + str(l) + "\n")
				leaf_count += increment
				
				# Create hosts, designated by letter h, and link to leaf
				for h in range(fanout):
					host_name = "h" + str(host_count)

					# Construct host UID MAC address, first 24 bits are reserved,
					# last 24 bits uniquely identify a host
					mac_addr = "dc:dc:dc:" + format((host_count >> 16) & 0xFF, "02x")
					mac_addr += ":" + format((host_count >> 8) & 0xFF, "02x")
					mac_addr += ":" + format(host_count & 0xFF, "02x")

					# Construct host RMAC address based on dc, pod, leaf, and host
					# First 2 bits are type (unused), next 10 are the data center id,
					# next 12 are pod the number, next 12 are the leaf number, and
					# last 12 are the host number
					rmac_addr = "00:1" + format((p >> 8) & 0xF, "01x") + ":"
					rmac_addr += format(p & 0xFF, "02x") + ":"
					rmac_addr += format((l >> 4) & 0xFF, "02x") + ":"
					rmac_addr += format(l & 0xF, "01x") + format((h >> 8)& 0xF, "01x")
					rmac_addr += ":" + format(h & 0xFF, "02x")

					# print(host_name + " UID-MAC : " + mac_addr + " RMAC: " + rmac_addr)
					self.addHost(host_name, mac = mac_addr)
					host_config.write(host_name + "," + leaf_name + ",")
					host_config.write(str(h) + "," + mac_addr + "\n")
					host_count += 1
					self.addLink(leaf_name, host_name, bw = 10, delay = "2ms")

			# Create spines, designated by letter s, and link to super spines and leaves
			for s in range(spine):
				spine_name = "s" + str(spine_count)
				self.addSwitch(spine_name)
				switch_config.write(spine_name + ",1," + str(p) + ",N/A\n")
				spine_count += increment
				for ss in range(ss_ratio):
					self.addLink(ss_switches[ss + s * ss_ratio], spine_name,
									bw = 40, delay = "2ms")
				for l in range(leaf):
					self.addLink(spine_name, leaf_switches[l + p * leaf],
									bw = 40, delay = "2ms")



if __name__ == "__main__":
	net = None
	try:
		setLogLevel("info")
		leaf, spine, pod, ss_ratio, fanout = parseOptions()
		topo = FoldedClos(leaf, spine, pod, ss_ratio, fanout)
		net = Mininet(topo, controller=RemoteController, link=TCLink)
		net.start()

		# Assign IPv6 addresses based on DCnet specifications
		for h in range(len(net.hosts)):
			host = net.hosts[h]
			command = "ifconfig " + host.name + "-eth0 inet6 add dcdc::dc"
			command += format(((h + 1) >> 16) & 0xFF, "02x")
			command += ":" + format((h + 1) & 0xFFFF, "04x") + "/104"
			host.cmd(command)

		# Run ping and TCP tests
		print("*** Running performance tests")
		#runPingTests(net, pod)
		#runTCPTests(net)

		CLI(net)
	finally:
		if net is not None:
			net.stop()

'''
topos = {'FoldedClos':
		(lambda leaf, spine, pod, ss_ratio, fanout:
		FoldedClos(leaf, spine, pod, ss_ratio, fanout))}
'''
