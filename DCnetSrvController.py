from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, nicira_ext
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.topology import event
from ryu.app.wsgi import WSGIApplication

class   DCnetSrvController (app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi' : WSGIApplication}

    def __init__ (self, *args, **kwargs):
        super(DCnetSrvController, self).__init__(*args, **kwargs)

    # Handle a switch joining the controller
    @set_ev_cls (event.EventSwitchEnter, MAIN_DISPATCHER)
    def switch_enter_handler (self, ev):

        switch = ev.switch
        dp = switch.dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # Add a rule to handle packets coming in from physical port
        # The eth_dst must be RMAC and must be replaced by the MAC
        match = parser.OFPMatch(in_port=1,
                                eth_type=0x86dd,
                                eth_dst=('dc:dc:dc:00:00:00', 'ff:ff:ff:00:00:00'))
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

        # Add a rule for packets to be sent out the physical port
        match = parser.OFPMatch(eth_dst=('98:98:98:00:00:00', 'ff:ff:ff:00:00:00'))
        action = parser.OFPActionOutput(1)
        instr = parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [action])
        flowmod = parser.OFPFlowMod(datapath=dp,
                                    table_id=0,
                                    priority=500,
                                    match=match,
                                    instructions=[instr])
        dp.send_msg(flowmod)
