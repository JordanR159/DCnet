from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import RemoteController, Node, Host, OVSKernelSwitch

from mininet.link import TCLink
from argparse import ArgumentParser

# Function to parse the command line arguments
def parseOptions():
	leaf = 4
	spine = 2
	pod = 4
	ss_ratio = 2
	fanout = 3

	parser = ArgumentParser("Create a folded Clos network topology")

	# Add arguments to the parser for leaf, spine, pod, super spine, and fanout options
	parser.add_argument("--leaf", type = int, help = "Number of Leaf switches per Pod")
	parser.add_argument("--spine", type = int, help = "Number of Spine switches per Pod")
	parser.add_argument("--pod", type = int, help = "Number of Pods in topology")
	parser.add_argument("--ratio", type = int
						, help = "Number of Super Spine switches per Spine switch")
	parser.add_argument("--fanout", type = int, help = "Number of hosts per Leaf switch")

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
		ss_count = 10 + increment
		spine_count = 11 + increment
		leaf_count = 12 + increment

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
					self.addLink(leaf_name, host_name)

			# Create spines, designated by letter s, and link to super spines and leaves
			for s in range(spine):
				spine_name = "s" + str(spine_count)
				self.addSwitch(spine_name)
				switch_config.write(spine_name + ",1," + str(p) + ",N/A\n")
				spine_count += increment
				for ss in range(ss_ratio):
					self.addLink(ss_switches[ss + s * ss_ratio], spine_name)
				for l in range(leaf):
					self.addLink(spine_name, leaf_switches[l + p * leaf])

if __name__ == "__main__":
	try:
		setLogLevel("info")
		leaf, spine, pod, ss_ratio, fanout = parseOptions()
		topo = FoldedClos(leaf, spine, pod, ss_ratio, fanout)
		net = Mininet(topo, controller=RemoteController)
		net.start()

		# Assign IPv6 addresses based on DCnet specifications
		for h in range(len(net.hosts)):
			host = net.hosts[h]
			command = "ifconfig " + host.name + "-eth0 inet6 add dcdc::dc"
			command += format(((h + 1) >> 16) & 0xFF, "02x")
			command += ":" + format((h + 1) & 0xFFFF, "04x") + "/104"
			host.cmd(command)
		CLI(net)
	finally:
		net.stop()

'''
topos = {'FoldedClos':
		(lambda leaf, spine, pod, ss_ratio, fanout:
		FoldedClos(leaf, spine, pod, ss_ratio, fanout))}
'''
