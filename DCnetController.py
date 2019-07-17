from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, nicira_ext
from ryu.ofproto.ofproto_protocol import ProtocolDesc
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.controller import ofp_event
from ryu.topology import event
from ryu.lib import addrconv
from ryu.lib.packet import packet
from ryu.topology import event

from ryu.app.wsgi import WSGIApplication
#from DCnetRestAPIManager import DCnetRestAPIManager
import time
import array


class	DCnetController (app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	_CONTEXTS = {"wsgi" : WSGIApplication}

	def __init__ (self, *args, **kwargs):
		super(DCnetController, self).__init__(*args, **kwargs)
		
		# Configure switches in DB from configuration CSV file
		self.switchDB = {}
		switch_config = open("switch_config.csv", "r")
		switch_config.readline()
		line = switch_config.readline()
		while line != "":
			config = line.split(",")
			line = switch_config.readline()
			self.switchDB[int(config[0][1:])] = {	
				"name" : config[0],
				"level" : int(config[1]),
				"dc" : int(config[2]),
				"pod" : int(config[3]),
				"leaf" : int(config[4][:-1]),
				"joined" : 0 }	
		self.n_joined = 0

		# Configure hosts in DB from configuration CSV file
		self.hostDB = {}
		host_config = open("host_config.csv", "r")
		host_config.readline()
		line = host_config.readline()
		while line != "":
			config = line.split(",")
			line = host_config.readline()
			self.hostDB[config[0][1:]] = {
				"name" : config[0],
				"leaf" : config[1],
				"port" : config[2],
				"rmac" : config[3][:-1]}

		# Configure port radix for switches from CSV file
		top_config = open("top_config.csv", "r")
		top_config.readline()
		config = top_config.readline().split(",")
		self.dc_count = int(config[0])
		self.dc_radix_down = int(config[1])
		self.ss_radix_down = int(config[2])
		self.sp_radix_up = int(config[3])
		self.sp_radix_down = int(config[4])
		self.lf_radix_up = int(config[5])
		self.lf_radix_down = int(config[6])

		# VMs in the DC
		self.vms = {}

		self.nextuid = 1

		# Register the Rest API Manager
		wsgi = kwargs["wsgi"]
		print wsgi
		#print wsgi.register(L2Switch, { "controller" : self })

	# Handle a new switch joining
	@set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
	def switch_enter_handler (self, ev):

		switch = ev.switch
		dpid = switch.dp.id

		# Check if the switch is in our database of switches
		if dpid in self.switchDB.keys():

			print "Switch ", dpid, "connected!!"
			print "Level: ", self.switchDB[dpid]["level"]
			print "Pod: ", self.switchDB[dpid]["pod"]
			print "Leaf: ", self.switchDB[dpid]["leaf"]

			self.switchDB[dpid]["object"] = switch

			# Depending on its position, add flows in it
			if self.switchDB[dpid]["level"] == 0:
				self.add_flows_dc(switch)
			elif self.switchDB[dpid]["level"] == 1:
				self.add_flows_super(switch)
			elif self.switchDB[dpid]["level"] == 2:
				self.add_flows_spine(switch)
			elif self.switchDB[dpid]["level"] == 3:
				self.add_flows_leaf(switch)
				if self.switchDB[dpid]["joined"] == 0:
					self.switchDB[dpid]["joined"] = 1
					self.n_joined += 1
					#for h in range(len(self.hostDB)):
					#	if self.hostDB[h]["leaf"] == self.switchDB[dpid]["name"]:
					#		self.create_vm(srvname = self.hostDB[h]["name"],
					#						uid = h, switch = self.switchDB[dpid])

			self.switchDB[dpid]["joined"] = 1
		#else:
		#	for vm in self.vms.values():
		#		self.create_vm(srvname = vm['server'], uid=vm['uid'], switch = self.switchDB[dpid])

	# Handle translation from ID MAC to RMAC and back at leaf switch
	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def packet_in_handler(self, ev):
		print "hello"

	# Add flows in a data center access switch
	def add_flows_dc (self, switch = None):
		dp = switch.dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser
		config = self.switchDB[dp.id]

		# Construct ethernet address to match for each connected pod
		eth_addr = format((config["dc"] >> 4) & 0x3F, "02x") + ":"
		eth_addr += format(config["dc"] & 0xF, "01x")
		eth_addr += "0:00:00:00:00"

		# Match the Data Center ID in the RMAC and forward accordingly
		match = parser.OFPMatch(eth_dst = (eth_addr, "ff:f0:00:00:00:00"))
		
		# ECMP flows down to the data center's super spines
		action = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
									   fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
									   basis=0,
									   slave_type=nicira_ext.NXM_OF_IN_PORT,
									   n_slaves=self.dc_radix_down,
									   ofs_nbits=0,
									   dst=0,
									   slaves=range(1, self.dc_radix_down + 1))
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=1000,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

		for d in range(self.dc_count):

			if d == config["dc"]:
				continue

			# Construct ethernet address to match for each connected pod
			eth_addr = format((d >> 4) & 0x3F, "02x") + ":"
			eth_addr += format(d & 0xF, "01x")
			eth_addr += "0:00:00:00:00"

			# Match the POD ID in the RMAC and forward accordingly
			match = parser.OFPMatch(eth_dst = (eth_addr, "ff:f0:00:00:00:00"))
			action = parser.OFPActionOutput(d + self.dc_radix_down + 1)
			instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										priority=500,
										match=match,
										instructions=[instr])
			dp.send_msg(flowmod)
			barrier = parser.OFPBarrierRequest(dp)
			dp.send_msg(barrier)

		
		# Send all other traffic to internet
		# TODO: Figure out how to do this
		match = parser.OFPMatch(eth_dst = ("00:00:00:00:00:00", "c0:00:00:00:00:00"))
		action = parser.OFPActionOutput(0)
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=100,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

	# Add flows in a super spine switch
	def add_flows_super (self, switch = None):

		dp = switch.dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser
		config = self.switchDB[dp.id]

		for p in range(self.ss_radix_down):

			# Construct ethernet address to match for each connected pod
			eth_addr = format((config["dc"] >> 4) & 0x3F, "02x") + ":"
			eth_addr += format(config["dc"] & 0xF, "01x")
			eth_addr += format((p >> 8) & 0xF, "01x") + ":"
			eth_addr += format(p & 0xFF, "02x") + ":"
			eth_addr += "00:00:00"

			# Match the POD ID in the RMAC and forward accordingly
			match = parser.OFPMatch(eth_dst = (eth_addr, "ff:ff:ff:00:00:00"))
			action = parser.OFPActionOutput(p + 1)
			instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										priority=1000,
										match=match,
										instructions=[instr])
			dp.send_msg(flowmod)
			barrier = parser.OFPBarrierRequest(dp)
			dp.send_msg(barrier)

		# Send traffic destined for another data center or internet to dc access switch
		match = parser.OFPMatch(eth_dst=("00:00:00:00:00:00", "c0:00:00:00:00:00"))
		action = parser.OFPActionOutput(self.ss_radix_down + 1)
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=500,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

	# Add flows in a spine switch
	def add_flows_spine (self, switch = None):

		dp = switch.dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser
		config = self.switchDB[dp.id]

		# Handle flows that remain in the pod
		for l in range(self.sp_radix_down):

			# Construct ethernet address to match for each connected pod
			eth_addr = format((config["dc"] >> 4) & 0x3F, "02x") + ":"
			eth_addr += format(config["dc"] & 0xF, "01x")
			eth_addr += format((config["pod"] >> 8) & 0xF, "01x") + ":"
			eth_addr += format(config["pod"] & 0xFF, "02x") + ":"
			eth_addr += format((l >> 4) & 0xFF, "02x") + ":"
			eth_addr += format(l & 0xF, "01x")
			eth_addr += "0:00"

			# Match the POD ID and LEAF ID in the RMAC and forward accordingly
			match = parser.OFPMatch(eth_dst = (eth_addr, "ff:ff:ff:ff:f0:00"))
			action = parser.OFPActionOutput(l + 1)
			instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										priority=1000,
										match=match,
										instructions=[instr])
			dp.send_msg(flowmod)
			barrier = parser.OFPBarrierRequest(dp)
			dp.send_msg(barrier)

		# Handle flows that are destined to other pods
		# ECMP the flow towards the super spine switches
		match = parser.OFPMatch(eth_dst=("00:00:00:00:00:00", "c0:00:00:00:00:00"))
		action = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
									   fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
									   basis=0,
									   slave_type=nicira_ext.NXM_OF_IN_PORT,
									   n_slaves=self.sp_radix_up,
									   ofs_nbits=0,
									   dst=0,
					slaves=range(self.sp_radix_down + 1,
								self.sp_radix_up + self.sp_radix_down + 1))
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=500,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

	# Add flows in a leaf switch
	def add_flows_leaf (self, switch = None):

		dp = switch.dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser
		config = self.switchDB[dp.id]

		# If the ethernet destination is an RMAC use it to forward the packet
		for h in range(self.lf_radix_down):

			# Construct ethernet address to match for each connected pod
			eth_addr = format((config["dc"] >> 4) & 0x3F, "02x") + ":"
			eth_addr += format(config["dc"] & 0xF, "01x")
			eth_addr += format((config["pod"] >> 8) & 0xF, "01x") + ":"
			eth_addr += format(config["pod"] & 0xFF, "02x") + ":"
			eth_addr += format((config["leaf"] >> 4) & 0xFF, "02x") + ":"
			eth_addr += format(config["leaf"] & 0xF, "01x")
			eth_addr += format((h >> 8) & 0xF, "01x") + ":"
			eth_addr += format(h & 0xFF, "02x")
			
			print eth_addr
			match = parser.OFPMatch(eth_dst = eth_addr)
			action = parser.OFPActionOutput(h + 1)
			instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										priority=1000,
										match=match,
										instructions=[instr])
			dp.send_msg(flowmod)
			barrier = parser.OFPBarrierRequest(dp)
			dp.send_msg(barrier)

		# Handle flows that are destined to other leaves
		# ECMP the flow towards the spine switches
		match = parser.OFPMatch(eth_dst=("00:00:00:00:00:00", "c0:00:00:00:00:00"))
		action = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
									   fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
									   basis=0,
									   slave_type=nicira_ext.NXM_OF_IN_PORT,
									   n_slaves=self.lf_radix_up,
									   ofs_nbits=0,
									   dst=0,
					slaves=range(self.lf_radix_down + 1,
								self.lf_radix_up + self.lf_radix_down + 1))
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=500,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)



		

"""

	def create_vm (self, srvname, uid=None, switch=None, slp=0):

		if srvname not in self.servers.keys():
			return None

		if uid == None or uid not in self.vms.keys():
			uid = self.nextuid
			self.nextuid = self.nextuid + 1
			self.vms[uid] = {'uid' : uid, 'mac' : '98:98:98:00:00:{0:02x}'.format(uid), 'server' : srvname}
		vm = self.vms[uid]

		if switch == None:
			switches = self.switchDB.values()
		else:
			switches = [switch]

		#print 'controller.create_vm :: sleeping for', slp
		#time.sleep(slp)
		#print 'controller.create_vm :: out of sleep'

		n = len(self.dummy_list)
		for i in range(0, slp):
			s = self.dummy_list[i % n]

			#print 'create_vm :: adding flow to dummy', s
			dp = s.dp
			ofp = dp.ofproto
			parser = dp.ofproto_parser

			match = parser.OFPMatch(eth_dst=vm['mac'])
			action = parser.OFPActionOutput(1)
			instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										priority=1000,
										match=match,
										instructions=[instr])
			dp.send_msg(flowmod)
			#barrier = parser.OFPBarrierRequest(dp)
			#dp.send_msg(barrier)

		for s in switches:

			#print s
			if s['name'] == 'dummy':
				continue

			if s['level'] != 2:
				continue

			if 'object' not in s.keys():
				continue

			dp = s['object'].dp
			ofp = dp.ofproto
			parser = dp.ofproto_parser

			if self.servers[srvname]['edge'] == s['name']:

				match = parser.OFPMatch(eth_dst=vm['mac'])
				action = parser.OFPActionOutput(self.servers[srvname]['port'])
				instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
				flowmod = parser.OFPFlowMod(datapath=dp,
											table_id=0,
											priority=1000,
											match=match,
											instructions=[instr])
				dp.send_msg(flowmod)
				barrier = parser.OFPBarrierRequest(dp)
				dp.send_msg(barrier)
			else:

				match = parser.OFPMatch(eth_dst=vm['mac'])
				action1 = parser.OFPActionSetField(eth_dst=self.servers[srvname]['rmac'])
				action2 = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
												fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
												basis=0,
												slave_type=nicira_ext.NXM_OF_IN_PORT,
												n_slaves=self.radix/2,
												ofs_nbits=0,
												dst=0,
												slaves=range(1+(self.radix/2), 1+self.radix))
				instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action1, action2])
				flowmod = parser.OFPFlowMod(datapath=dp,
											table_id=0,
											priority=1000,
											match=match,
											instructions=[instr])
				dp.send_msg(flowmod)
				barrier = parser.OFPBarrierRequest(dp)
				dp.send_msg(barrier)

		return uid

	def create_tmp_vm (self, uid, src, dst):

		swname = self.servers[src]['edge']

		edge = None
		for s in self.switchDB.values():
			if s['name'] == swname:
				edge = s
				break

		if edge == None:
			return

		if 'object' not in edge.keys():
			return

		dp = edge['object'].dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser

		match = parser.OFPMatch(eth_type=0x86dd,
								ipv6_dst='dc98::9898:9800:{0:02x}'.format(uid))
		action2 = parser.OFPActionSetField(eth_dst=self.servers[dst]['rmac'])
		action1 = parser.OFPActionSetField(in_port_nxm=1)
		action3 = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
										fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
										basis=0,
										slave_type=nicira_ext.NXM_OF_IN_PORT,
										n_slaves=self.radix/2,
										ofs_nbits=0,
										dst=0,
										slaves=range(1+(self.radix/2), 1+self.radix))
		instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action1, action2, action3])
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									priority=1001,
									match=match,
									instructions=[instr])
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

	def delete_tmp_vm (self, uid, src):

		swname = self.servers[src]['edge']

		edge = None
		for s in self.switchDB.values():
			if s['name'] == swname:
				edge = s
				break

		if edge == None or 'object' not in edge.keys():
			return

		dp = edge['object'].dp
		ofp = dp.ofproto
		parser = dp.ofproto_parser

		match = parser.OFPMatch(eth_type=0x86dd,
								ipv6_dst='dc98::9898:9800:{0:02x}'.format(uid))
		flowmod = parser.OFPFlowMod(datapath=dp,
									table_id=0,
									match=match,
									out_port=ofp.OFPP_ANY,
									out_group=ofp.OFPG_ANY,
									command=ofp.OFPFC_DELETE)
		dp.send_msg(flowmod)
		barrier = parser.OFPBarrierRequest(dp)
		dp.send_msg(barrier)

	def delete_vm (self, uid):

		if uid not in self.vms.keys():
			return None

		server = self.vms[uid]['server']

		for s in self.switchDB.values():

			if s['name'] == 'dummy':
				continue

			if s['level'] != 2:
				continue

			if 'object' not in s.keys():
				continue

			dp = s['object'].dp
			ofp = dp.ofproto
			parser = dp.ofproto_parser

			match = parser.OFPMatch(eth_dst=self.vms[uid]['mac'])
			flowmod = parser.OFPFlowMod(datapath=dp,
										table_id=0,
										match=match,
										out_port=ofp.OFPP_ANY,
										out_group=ofp.OFPG_ANY,
										command=ofp.OFPFC_DELETE)
			dp.send_msg(flowmod)
			barrier = parser.OFPBarrierRequest(dp)
			dp.send_msg(barrier)

"""
