from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, nicira_ext
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.topology import event
from ryu.app.wsgi import WSGIApplication

class   DCnetSrvController (app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi' : WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DCnetSrvController, self).__init__(*args, **kwargs)

        self.server_names = ["dcnet-srv000", "dcnet-srv001", "dcnet-srv010", "dcnet-srv011", "dcnet-srv100", "dcnet-srv101", "dcnet-srv110", "dcnet-srv111"]
        self.switch_connected = 0

        self.vms = {}

        self.next_ofport = 3

    @set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
    def handle_switch_enter (self, ev):

        if self.switch_connected == 1:
            return

        switch = ev.switch
        dpid = switch.dp.id

        if dpid > len(self.server_names):
            return

        name = self.server_names[dpid-1]
        print "Server: {0}".format(name)
        self.srvname = name
        self.uid = self.server_names.index(self.srvname)
        print 'Server UID is {0}'.format(self.uid)

        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # Add a flow rule to handle packets coming in on phisical NIC
        # The eth_dst must be an RMAC and we must restore the UID-MAC
        # from the destination IPv6 address
        match = parser.OFPMatch(in_port=1,
                                eth_dst=('dc:dc:dc:00:00:00','ff:ff:ff:00:00:00'),
                                eth_type=0x86dd)
        action1 = parser.NXActionRegMove(src_field="ipv6_dst_nxm",
                                         dst_field="eth_dst_nxm",
                                         n_bits=48,
                                         src_ofs=0,
                                         dst_ofs=0)
        action2 = parser.NXActionResubmitTable(table_id=0)
        instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action1, action2])
        flowmod = parser.OFPFlowMod(datapath=dp,
                                    table_id=0,
                                    priority=1000,
                                    match=match,
                                    instructions=[instr])
        dp.send_msg(flowmod)

        # Add a flow rule for packets leaving the server
        # eth_dst must be a UID-MAC
        match = parser.OFPMatch(eth_dst=('98:98:98:00:00:00','ff:ff:ff:00:00:00'))
        action = parser.OFPActionOutput(1)
        instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
        flowmod = parser.OFPFlowMod(datapath=dp,
                                    table_id=0,
                                    priority=500,
                                    match=match,
                                    instructions=[instr])
        dp.send_msg(flowmod)

        # Add a flow rule for connectivity to the hypervisor interface
        match = parser.OFPMatch(eth_dst='98:98:98:00:00:{0:02x}'.format(self.uid))
        action = parser.OFPActionOutput(2)
        instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
        flowmod = parser.OFPFlowMod(datapath=dp,
                                    table_id=0,
                                    priority=1000,
                                    match=match,
                                    instructions=[instr])
        dp.send_msg(flowmod)
