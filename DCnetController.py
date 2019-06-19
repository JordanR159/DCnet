from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, nicira_ext
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.topology import event
from ryu.app.wsgi import WSGIApplication
from DCnetRestAPIManager import DCnetRestAPIManager
import time

class   DCnetController (app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi' : WSGIApplication}

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
			switchDB[config[0][1:]] = {	
				"name" : config[0],
				"level" : config[1],
				"pod" : config[2],
				"leaf" : config[3][:-1]
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
			hostDB[config[0][1:]] = {
				"name" : config[0],
				"leaf" : config[1],
				"port" : config[2],
				"rmac" : config[3][:-1]}
        # VMs in the DC
        self.vms = {}

        self.nextuid = 1

        # Register the Rest API Manager
        wsgi = kwargs['wsgi']
	print wsgi
        print wsgi.register(DCnetRestAPIManager, { 'controller' : self })

    # Handle a new switch joining
    @set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
    def switch_enter_handler (self, ev):

        switch = ev.switch
        dpid = switch.dp.dpid

        # Check if the switch is in our database of switches
        if dpid in self.switchDB.keys():

            print 'Switch ', dpid, 'connected!!'
            print 'Level: ', self.switchDB[dpid]['level']
            print 'Pod: ', self.switchDB[dpid]['pod']
            print 'Leaf: ', self.switchDB[dpid]['leaf']

            self.switchDB[ip]['object'] = switch

            # Depending on its position, add flows in it
            if self.switchDB[ip]['level'] == 0:
                self.add_flows_super(switch)
            elif self.switchDB[ip]['level'] == 1:
                self.add_flows_spine(switch)
            elif self.switchDB[ip]['level'] == 2:
                self.add_flows_leaf(switch)

        if self.switchDB[ip]['joined'] == 0:
            self.switchDB[ip]['joined'] = 1
            self.n_joined += 1
			
            self.create_vm(srvname="dcnet-srv000", uid=0, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv001", uid=1, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv010", uid=2, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv011", uid=3, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv100", uid=4, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv101", uid=5, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv110", uid=6, switch=self.switchDB[ip])
            self.create_vm(srvname="dcnet-srv111", uid=7, switch=self.switchDB[ip])
        else:
            for vm in self.vms.values():
                self.create_vm(srvname=vm['server'], uid=vm['uid'], switch=self.switchDB[ip])

    # Add flows in a core switch
    def add_flows_core (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        for i in range(self.radix):

            # Match the POD ID in the RMAC and forward accordingly
            match = parser.OFPMatch(eth_dst=('dc:dc:dc:%s:00:00' % (i), 'ff:ff:ff:ff:00:00'))
            action = parser.OFPActionOutput(i+1)
            instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
            flowmod = parser.OFPFlowMod(datapath=dp,
                                        table_id=0,
                                        priority=1000,
                                        match=match,
                                        instructions=[instr])

            dp.send_msg(flowmod)
            barrier = parser.OFPBarrierRequest(dp)
            dp.send_msg(barrier)

    # Add flows in an aggregate switch
    def add_flows_aggr (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        ip = dp.address[0]
        pod = self.switchDB[ip]['pod']
        column = self.switchDB[ip]['column']

        # Handle flows that remain in the pod
        for i in range(self.radix/2):

            # Match the pod number and the column number and forward accordingly
            dst='dc:dc:dc:{0:02x}:{1:02x}:00'.format(pod, i)
            match = parser.OFPMatch(eth_dst=(dst, 'ff:ff:ff:ff:ff:00'))
            action = parser.OFPActionOutput(i+1)
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
        # ECMP the flow towards the core switches
        match = parser.OFPMatch(eth_dst=('dc:dc:dc:00:00:00', 'ff:ff:ff:00:00:00'))
        action = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
                                       fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
                                       basis=0,
                                       slave_type=nicira_ext.NXM_OF_IN_PORT,
                                       n_slaves=self.radix/2,
                                       ofs_nbits=0,
                                       dst=0,
                                       slaves=range(1+(self.radix/2), self.radix+1))
        instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
        flowmod = parser.OFPFlowMod(datapath=dp,
                                    table_id=0,
                                    priority=500,
                                    match=match,
                                    instructions=[instr])

        dp.send_msg(flowmod)
        barrier = parser.OFPBarrierRequest(dp)
        dp.send_msg(barrier)

    # Add flows in an edge switch
    def add_flows_edge (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        ip = dp.address[0]
        pod = self.switchDB[ip]['pod']
        column = self.switchDB[ip]['column']

        # If the ethernet destination is an RMAC use it to forward the packet
        for i in range(0, self.radix/2):

            match = parser.OFPMatch(eth_dst='dc:dc:dc:{0:02x}:{1:02x}:{2:02x}'.format(pod, column, i))
            action = parser.OFPActionOutput(i+1)
            instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
            flowmod = parser.OFPFlowMod(datapath=dp,
                                        table_id=0,
                                        priority=1000,
                                        match=match,
                                        instructions=[instr])

            dp.send_msg(flowmod)
            barrier = parser.OFPBarrierRequest(dp)
            dp.send_msg(barrier)

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
