from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, nicira_ext
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.topology import event

class   DCnetController (app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__ (self, *args, **kwargs):
        super(DCnetController, self).__init__(*args, **kwargs)

        self.switchDB = {}
        self.switchDB['128.10.135.31'] = { 'name' : 'core0', 'level' : 0, 'pod' : 0, 'column' : 0 }
        self.switchDB['128.10.135.32'] = { 'name' : 'core1', 'level' : 0, 'pod' : 0, 'column' : 1 }
        self.switchDB['128.10.135.33'] = { 'name' : 'aggr00', 'level' : 1, 'pod' : 0, 'column' : 0 }
        self.switchDB['128.10.135.34'] = { 'name' : 'aggr01', 'level' : 1, 'pod' : 0, 'column' : 1 }
        self.switchDB['128.10.135.35'] = { 'name' : 'edge00', 'level' : 2, 'pod' : 0, 'column' : 0 }
        self.switchDB['128.10.135.36'] = { 'name' : 'edge01', 'level' : 2, 'pod' : 0, 'column' : 1 }
        self.switchDB['128.10.135.37'] = { 'name' : 'aggr10', 'level' : 1, 'pod' : 1, 'column' : 0 }
        self.switchDB['128.10.135.38'] = { 'name' : 'aggr11', 'level' : 1, 'pod' : 1, 'column' : 1 }
        self.switchDB['128.10.135.39'] = { 'name' : 'edge10', 'level' : 2, 'pod' : 1, 'column' : 0 }
        self.switchDB['128.10.135.40'] = { 'name' : 'edge11', 'level' : 2, 'pod' : 1, 'column' : 1 }
        self.radix = 4
        self.vms = [ { 'ip' : '10.0.0.1', 'mac' : 'd4:ae:52:c9:a8:34', 'edge' : 'edge00', 'rmac' : 'dc:dc:dc:00:00:00', 'port' : 1},
                     { 'ip' : '10.0.0.2', 'mac' : 'd4:ae:52:c9:ab:16', 'edge' : 'edge01', 'rmac' : 'dc:dc:dc:00:01:00', 'port' : 1},
                     { 'ip' : '10.0.0.3', 'mac' : 'd4:ae:52:c8:c3:61', 'edge' : 'edge10', 'rmac' : 'dc:dc:dc:01:00:00', 'port' : 1}]

    @set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
    def switch_enter_handler (self, ev):

        switch = ev.switch
        """
        for k in switch.__dict__.keys():
            print k, switch.__dict__[k]
        print 'Datapath fields:'
        for k in switch.dp.__dict__.keys():
            print k, switch.dp.__dict__[k]
        """
        ip = switch.dp.address[0]

        if ip in self.switchDB.keys():
            print 'Switch ', ip, 'connected!!'
            print 'Level: ', self.switchDB[ip]['level']
            print 'Pod: ', self.switchDB[ip]['pod']
            print 'Column: ', self.switchDB[ip]['column']

            if self.switchDB[ip]['level'] == 0:
                self.add_flows_core(switch)
            elif self.switchDB[ip]['level'] == 1:
                self.add_flows_aggr(switch)
            elif self.switchDB[ip]['level'] == 2:
                self.add_flows_edge(switch)

    def add_flows_core (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        for i in range(self.radix):

            match = parser.OFPMatch(eth_dst=('dc:dc:dc:%s:00:00' % (i), 'ff:ff:ff:ff:00:00'))
            action = parser.OFPActionOutput(i+1)
            instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
            flowmod = parser.OFPFlowMod(datapath=dp,
                                        table_id=0,
                                        priority=1000,
                                        match=match,
                                        instructions=[instr])

            dp.send_msg(flowmod)

    def add_flows_aggr (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        ip = dp.address[0]
        pod = self.switchDB[ip]['pod']
        column = self.switchDB[ip]['column']

        for i in range(self.radix/2):

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

    def add_flows_edge (self, switch=None):

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        ip = dp.address[0]
        pod = self.switchDB[ip]['pod']
        column = self.switchDB[ip]['column']

        for v in self.vms:

            if v['edge'] == self.switchDB[ip]['name']:
                match = parser.OFPMatch(eth_dst=v['mac'])
                action = parser.OFPActionOutput(v['port'])
                instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
                flowmod = parser.OFPFlowMod(datapath=dp,
                                            table_id=0,
                                            priority=1000,
                                            match=match,
                                            instructions=[instr])

                dp.send_msg(flowmod)

                match = parser.OFPMatch(eth_dst=v['rmac'])
                action1 = parser.OFPActionSetField(eth_dst=v['mac'])
                action2 = parser.OFPActionOutput(v['port'])
                instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action1, action2])
                flowmod = parser.OFPFlowMod(datapath=dp,
                                            table_id=0,
                                            priority=1000,
                                            match=match,
                                            instructions=[instr])

                dp.send_msg(flowmod)
            else:
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
