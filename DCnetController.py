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

        # All the switches in the DC and their positions
        self.switchDB = {}
        self.switchDB['128.10.135.31'] = { 'name' : 'core0', 'level' : 0, 'pod' : 0, 'column' : 0, 'joined' : 0 }
        self.switchDB['128.10.135.32'] = { 'name' : 'core1', 'level' : 0, 'pod' : 0, 'column' : 1, 'joined' : 0}
        self.switchDB['128.10.135.33'] = { 'name' : 'aggr00', 'level' : 1, 'pod' : 0, 'column' : 0, 'joined' : 0 }
        self.switchDB['128.10.135.34'] = { 'name' : 'aggr01', 'level' : 1, 'pod' : 0, 'column' : 1, 'joined' : 0 }
        self.switchDB['128.10.135.35'] = { 'name' : 'edge00', 'level' : 2, 'pod' : 0, 'column' : 0, 'joined' : 0 }
        self.switchDB['128.10.135.36'] = { 'name' : 'edge01', 'level' : 2, 'pod' : 0, 'column' : 1, 'joined' : 0 }
        self.switchDB['128.10.135.37'] = { 'name' : 'aggr10', 'level' : 1, 'pod' : 1, 'column' : 0, 'joined' : 0 }
        self.switchDB['128.10.135.38'] = { 'name' : 'aggr11', 'level' : 1, 'pod' : 1, 'column' : 1, 'joined' : 0 }
        self.switchDB['128.10.135.39'] = { 'name' : 'edge10', 'level' : 2, 'pod' : 1, 'column' : 0, 'joined' : 0 }
        self.switchDB['128.10.135.40'] = { 'name' : 'edge11', 'level' : 2, 'pod' : 1, 'column' : 1, 'joined' : 0 }

        self.n_joined = 0

        # Radix of switches in the DC
        self.radix = 4

        # Servers in the DC
        self.servers = {}
        self.servers['dcnet-srv000'] = { 'uid' : 0, 'rmac' : 'dc:dc:dc:00:00:00', 'edge' : 'edge00', 'port' : 1, 'ip' : '128.10.135.41' }
        self.servers['dcnet-srv001'] = { 'uid' : 1, 'rmac' : 'dc:dc:dc:00:00:01', 'edge' : 'edge00', 'port' : 2 }
        self.servers['dcnet-srv010'] = { 'uid' : 2, 'rmac' : 'dc:dc:dc:00:01:00', 'edge' : 'edge01', 'port' : 1, 'ip' : '128.10.135.42' }
        self.servers['dcnet-srv011'] = { 'uid' : 3, 'rmac' : 'dc:dc:dc:00:01:01', 'edge' : 'edge01', 'port' : 2 }
        self.servers['dcnet-srv100'] = { 'uid' : 4, 'rmac' : 'dc:dc:dc:01:00:00', 'edge' : 'edge10', 'port' : 1, 'ip' : '128.10.135.43' }
        self.servers['dcnet-srv101'] = { 'uid' : 5, 'rmac' : 'dc:dc:dc:01:00:01', 'edge' : 'edge10', 'port' : 2 }
        self.servers['dcnet-srv110'] = { 'uid' : 6, 'rmac' : 'dc:dc:dc:01:01:00', 'edge' : 'edge11', 'port' : 1 }
        self.servers['dcnet-srv111'] = { 'uid' : 7, 'rmac' : 'dc:dc:dc:01:01:01', 'edge' : 'edge11', 'port' : 2 }

        # VMs in the DC
        self.vms = {}

        self.nextuid = 0
        """
        # VMs in the DC
        self.vms = [{ 'mac' : '00:00:98:00:00:00', 'edge' : 'edge00', 'rmac' : 'dc:dc:dc:00:00:00', 'port' : 1},
                    { 'mac' : '00:00:98:00:00:01', 'edge' : 'edge01', 'rmac' : 'dc:dc:dc:00:01:00', 'port' : 1},
                    { 'mac' : '00:00:98:00:00:02', 'edge' : 'edge10', 'rmac' : 'dc:dc:dc:01:00:00', 'port' : 1}]
        """

        # Register the Rest API Manager
        wsgi = kwargs['wsgi']
	print wsgi
        print wsgi.register(DCnetRestAPIManager, { 'controller' : self })

    # Handle a new switch joining
    @set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
    def switch_enter_handler (self, ev):

        switch = ev.switch
        ip = switch.dp.address[0]

        # Check if the switch is in our database of switches
        if ip in self.switchDB.keys():
            print 'Switch ', ip, 'connected!!'
            print 'Level: ', self.switchDB[ip]['level']
            print 'Pod: ', self.switchDB[ip]['pod']
            print 'Column: ', self.switchDB[ip]['column']

            self.switchDB[ip]['object'] = switch

            # Depending on its position, add flows in it
            if self.switchDB[ip]['level'] == 0:
                self.add_flows_core(switch)
            elif self.switchDB[ip]['level'] == 1:
                self.add_flows_aggr(switch)
            elif self.switchDB[ip]['level'] == 2:
                self.add_flows_edge(switch)

        if self.switchDB[ip]['joined'] == 0:
            self.switchDB[ip]['joined'] = 1
            self.n_joined = self.n_joined + 1

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

        """
        for v in self.vms:

            # Flows destined to a VM under this switch
            if v['edge'] == self.switchDB[ip]['name']:

                # If the Ethernet destination is the MAC of the VM just forward it
                match = parser.OFPMatch(eth_dst=v['mac'])
                action = parser.OFPActionOutput(v['port'])
                instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
                flowmod = parser.OFPFlowMod(datapath=dp,
                                            table_id=0,
                                            priority=1000,
                                            match=match,
                                            instructions=[instr])

                dp.send_msg(flowmod)
            else: # For VMs not under this switch

                # Rewrite the Ethernet destination with the RMAC and ECMP towards the aggregates
                match = parser.OFPMatch(eth_dst=v['mac'])
                action1 = parser.OFPActionSetField(eth_dst=v['rmac'])
                action2 = parser.NXActionBundle(algorithm=nicira_ext.NX_BD_ALG_HRW,
                                                fields=nicira_ext.NX_HASH_FIELDS_SYMMETRIC_L4,
                                                basis=0,
                                                slave_type=nicira_ext.NXM_OF_IN_PORT,
                                                n_slaves=self.radix/2,
                                                ofs_nbits=0,
                                                dst=0,
                                                slaves=range(1+(self.radix/2), self.radix+1))
                instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action1, action2])
                flowmod = parser.OFPFlowMod(datapath=dp,
                                            table_id=0,
                                            priority=1000,
                                            match=match,
                                            instructions=[instr])

                dp.send_msg(flowmod)
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

        print 'controller.create_vm :: sleeping for', slp
        time.sleep(slp)
        print 'controller.create_vm :: out of sleep'

        for s in switches:

            print s
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
        action1 = parser.OFPActionSetField(eth_dst=self.servers[dst]['rmac'])
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
                                    priority=1001,
                                    match=match,
                                    instructions=[instr])
        dp.send_msg(flowmod)

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

    def delete_vm (self, uid):

        if uid not in self.vms.keys():
            return None

        server = self.vms[uid]['server']

        for s in self.switchDB.values():

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
