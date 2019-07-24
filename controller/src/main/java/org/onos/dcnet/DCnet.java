/*
 * Copyright 2015 Open Networking Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *	   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.onos.dcnet;

import com.google.common.collect.HashMultimap;
import com.google.common.collect.SetMultimap;
import com.google.common.collect.Sets;
import org.apache.felix.scr.annotations.Activate;
import org.apache.felix.scr.annotations.Component;
import org.apache.felix.scr.annotations.Deactivate;
import org.apache.felix.scr.annotations.Reference;
import org.apache.felix.scr.annotations.ReferenceCardinality;
import org.onlab.packet.Ethernet;
import org.onlab.packet.IPv4;
import org.onlab.packet.MacAddress;
import org.onlab.util.KryoNamespace;
import org.onosproject.core.ApplicationId;
import org.onosproject.core.CoreService;
import org.onosproject.core.GroupId;
import org.onosproject.net.*;
import org.onosproject.net.device.DeviceEvent;
import org.onosproject.net.device.DeviceListener;
import org.onosproject.net.device.DeviceService;
import org.onosproject.net.flow.*;
import org.onosproject.net.flow.criteria.Criterion;
import org.onosproject.net.flow.criteria.EthCriterion;
import org.onosproject.net.flowobjective.DefaultForwardingObjective;
import org.onosproject.net.flowobjective.FlowObjectiveService;
import org.onosproject.net.flowobjective.ForwardingObjective;
import org.onosproject.net.group.GroupKey;
import org.onosproject.net.group.GroupService;
import org.onosproject.net.host.HostEvent;
import org.onosproject.net.host.HostListener;
import org.onosproject.net.host.HostService;
import org.onosproject.net.packet.PacketContext;
import org.onosproject.net.packet.PacketPriority;
import org.onosproject.net.packet.PacketProcessor;
import org.onosproject.net.packet.PacketService;
import org.onosproject.net.topology.PathService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import static org.onlab.util.Tools.groupedThreads;
import static org.onosproject.net.flow.FlowRuleEvent.Type.RULE_REMOVED;
import static org.onosproject.net.flow.criteria.Criterion.Type.ETH_SRC;

/**
 * Sample application that permits only one ICMP ping per minute for a unique
 * src/dst MAC pair per switch.
 */
@Component(immediate = true)
public class DCnet {
    /* Reference apps: oneping and group-fwd in https://github.com/opennetworkinglab/onos-app-samples */

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private CoreService coreService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private FlowObjectiveService flowObjectiveService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private FlowRuleService flowRuleService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private PacketService packetService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private DeviceService deviceService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private HostService hostService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private GroupService groupService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY_UNARY)
    private PathService pathService;

    public class SwitchEntry {
        private String name;
        private int level;
        private int dc;
        private int pod;
        private int leaf;
        private boolean joined;
        private Device device;

        public SwitchEntry(String name, int level, int dc, int pod, int leaf) {
            this.name = name;
            this.level = level;
            this.dc = dc;
            this.pod = pod;
            this.leaf = leaf;
            this.joined = false;
            this.device = null;
        }

        public String getName() {
            return this.name;
        }

        public int getLevel() {
            return this.level;
        }

        public int getDc() {
            return this.dc;
        }

        public int getPod() {
            return this.pod;
        }

        public int getLeaf() {
            return this.leaf;
        }

        public Device getDevice() {
            return this.device;
        }

        public void setDevice(Device device) {
            this.device = device;
        }

        public boolean isJoined() {
            return this.joined;
        }

        public void setJoined() {
            this.joined = true;
        }
    }

    public class HostEntry {
        private String name;
        private String leaf;
        private String port;
        private String rmac;

        public HostEntry(String name, String leaf, String port, String rmac) {
            this.name = name;
            this.leaf = leaf;
            this.port = port;
            this.rmac = rmac;
        }

        public String getName() {
            return this.name;
        }

        public String getLeaf() {
            return this.leaf;
        }

        public String getPort() {
            return this.port;
        }

        public String getRmac() {
            return this.rmac;
        }

    }

    private static Logger log = LoggerFactory.getLogger(DCnet.class);

    private static final String configLoc = "~/DCnet/";

    private static final int DC = 0;
    private static final int SUPER = 1;
    private static final int SPINE = 2;
    private static final int LEAF = 3;

    private int dcCount;
    private int dcRadixDown;
    private int ssRadixDown;
    private int spRadixUp;
    private int spRadixDown;
    private int lfRadixUp;
    private int lfRadixDown;

    /* Maps IP address to a switch entry */
    private Map<String, SwitchEntry> switchDB = new TreeMap<>();

    /* Maps IP address to a host entry */
    private Map<String, HostEntry> hostDB = new TreeMap<>();

    private ApplicationId appId;

    protected static KryoNamespace appKryo = new KryoNamespace.Builder()
            .register(Integer.class)
            .register(DeviceId.class)
            .build("group-fwd-app");

    private final SetMultimap<GroupKey, FlowRule> pendingFlows = HashMultimap.create();

    private final DeviceListener deviceListener = new InternalDeviceListener();

    private final PacketProcessor packetProcessor = new LeafPacketProcessor();

    // Selector for ICMP traffic that is to be intercepted
    private final TrafficSelector intercept = DefaultTrafficSelector.builder()
            .matchEthType(Ethernet.TYPE_IPV4).matchIPProtocol(IPv4.PROTOCOL_ICMP)
            .build();

    private void init() {
        switchDB = new TreeMap<>();
        hostDB = new TreeMap<>();

        try {
            BufferedReader switchConfig = new BufferedReader(new FileReader(configLoc + "switch_config.csv"));
            String line;
            switchConfig.readLine();
            while (!((line = switchConfig.readLine()).equals(""))) {
                String[] config = line.split(",");
                switchDB.put(config[0], new SwitchEntry(config[1], Integer.parseInt(config[2]),
                                                        Integer.parseInt(config[3]), Integer.parseInt(config[4]),
                                                        Integer.parseInt(config[5])));
            }

            BufferedReader hostConfig = new BufferedReader(new FileReader(configLoc + "host_config.csv"));
            hostConfig.readLine();
            while (!((line = hostConfig.readLine()).equals(""))) {
                String[] config = line.split(",");
                hostDB.put(config[0], new HostEntry(config[1], config[2], config[3], config[4]));
            }

            BufferedReader topConfig = new BufferedReader(new FileReader(configLoc + "top_config.csv"));
            topConfig.readLine();
            String[] config = topConfig.readLine().split(",");
            dcCount = Integer.parseInt(config[0]);
            dcRadixDown = Integer.parseInt(config[1]);
            ssRadixDown = Integer.parseInt(config[2]);
            spRadixUp = Integer.parseInt(config[3]);
            spRadixDown = Integer.parseInt(config[4]);
            lfRadixUp = Integer.parseInt(config[5]);
            lfRadixDown = Integer.parseInt(config[6]);
        }

        catch (IOException e) {
            e.printStackTrace();
        }
    }

    @Activate
    public void activate() {
        init();
        appId = coreService.registerApplication("org.onosproject.dcnet");
        //packetService.addProcessor(packetProcessor, 50000);
        packetService.requestPackets(intercept, PacketPriority.CONTROL, appId, Optional.empty());
        deviceService.addListener(deviceListener);
        log.info("Started");
    }

    @Deactivate
    public void deactivate() {
        //packetService.removeProcessor(packetProcessor);
        flowRuleService.removeFlowRulesById(appId);
        deviceService.removeListener(deviceListener);
        log.info("Stopped");
    }

    // Processes the specified ICMP ping packet.
    private void processPacket(PacketContext context, Ethernet eth) {
        DeviceId deviceId = context.inPacket().receivedFrom().deviceId();
        MacAddress src = eth.getSourceMAC();
        MacAddress dst = eth.getDestinationMAC();
        log.info(dst.toString());
        if (dst.toString().equals("00:0E:C6:D7:38:63")) {
            log.info("Dropping Packet");
            TrafficSelector selector = DefaultTrafficSelector.builder()
                    .matchEthSrc(src).matchEthDst(dst).build();

            TrafficTreatment drop = DefaultTrafficTreatment.builder()
                    .drop().build();

            flowObjectiveService.forward(deviceId, DefaultForwardingObjective.builder()
                    .fromApp(appId)
                    .withSelector(selector)
                    .withTreatment(drop)
                    .withFlag(ForwardingObjective.Flag.VERSATILE)
                    .withPriority(50000)
                    .add());
        }
    }


    // Indicates whether the specified packet corresponds IPv4
    private boolean isIPv4(Ethernet eth) {
        return eth.getEtherType() == Ethernet.TYPE_IPV4;
    }


    // Intercepts packets
    private class LeafPacketProcessor implements PacketProcessor {
        @Override
        public void process(PacketContext context) {
            Ethernet eth = context.inPacket().parsed();
            processPacket(context, eth);
        }
    }

    private synchronized void setupFlows(Device device) {
        String ip = device.chassisId().toString();
		log.info("IP " + ip + " connected");
        if (switchDB.containsKey(ip)) {
            SwitchEntry entry = switchDB.get(ip);
            log.info("Switch " + ip + " connected");
            log.info("Level: " + entry.getLevel());
            log.info("DC: " + entry.getDc());
            log.info("Pod: " + entry.getPod());
            log.info("Leaf: " + entry.getLeaf());

            entry.setDevice(device);
            switch (entry.getLevel()) {
                case DC:
                    addFlowsDC(device);
                    break;
                case SUPER:
                    addFlowsSuper(device);
                    break;
                case SPINE:
                    addFlowsSpine(device);
                    break;
                case LEAF:
                    addFlowsLeaf(device);
                    break;
                default:
                    break;
            }
            entry.setJoined();


        }
    }

    private void addFlowsDC(Device device) {
        String ip = device.id().uri().getHost();
        SwitchEntry entry = switchDB.get(ip);
        int dc = entry.getDc();
        byte[] bytes = new byte[6];
        bytes[0] = (byte)((dc >> 4) & 0x3F);
        bytes[1] = (byte)((dc & 0xF) << 4);
        MacAddress eth = new MacAddress(bytes);
        MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xF0, 0x00, 0x00, 0x00, 0x00});
        TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask);
        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(hashSelector(1, dcRadixDown, entry));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withSelector(selector.build())
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(1000)
                .build();
        flowRuleService.applyFlowRules(flowRule);

        for (int d = 0; d < dcCount; d++) {
            bytes = new byte[6];
            bytes[0] = (byte)((d >> 4) & 0x3F);
            bytes[1] = (byte)((d & 0xF) << 4);
            eth = new MacAddress(bytes);
            selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask);
            treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(dcRadixDown + d + 1));
            flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(500)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }
        // TODO: Forward all other traffic to internet
    }

    private void addFlowsSuper(Device device) {
        String ip = device.id().uri().getHost();
        SwitchEntry entry = switchDB.get(ip);
        int dc = entry.getDc();
        for (int p = 0; p < ssRadixDown; p++) {
            byte[] bytes = new byte[6];
            bytes[0] = (byte) ((dc >> 4) & 0x3F);
            bytes[1] = (byte) (((dc & 0xF) << 4) + ((p >> 8) & 0xF));
            bytes[2] = (byte) (p & 0xFF);
            MacAddress eth = new MacAddress(bytes);
            MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xFF, (byte) 0xFF, 0x00, 0x00, 0x00});
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(p + 1));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }

        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(ssRadixDown + 1));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(500)
                .build();
        flowRuleService.applyFlowRules(flowRule);
    }

    private void addFlowsSpine(Device device) {
        String ip = device.id().uri().getHost();
        SwitchEntry entry = switchDB.get(ip);
        int dc = entry.getDc();
        int pod = entry.getPod();
        for (int l = 0; l < spRadixDown; l++) {
            byte[] bytes = new byte[6];
            bytes[0] = (byte) ((dc >> 4) & 0x3F);
            bytes[1] = (byte) (((dc & 0xF) << 4) + ((pod >> 8) & 0xF));
            bytes[2] = (byte) (pod & 0xFF);
            bytes[3] = (byte) ((l >> 4) & 0xFF);
            bytes[4] = (byte) ((l & 0xF) << 4);
            MacAddress eth = new MacAddress(bytes);
            MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xF0, 0x00});
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(l + 1));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }

        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(hashSelector(spRadixDown + 1, spRadixUp, entry));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(500)
                .build();
        flowRuleService.applyFlowRules(flowRule);
    }

    private void addFlowsLeaf(Device device) {
        String ip = device.id().uri().getHost();
        SwitchEntry entry = switchDB.get(ip);
        int dc = entry.getDc();
        int pod = entry.getPod();
        int leaf = entry.getLeaf();
        for (int h = 0; h < lfRadixDown; h++) {
            byte[] bytes = new byte[6];
            bytes[0] = (byte) ((dc >> 4) & 0x3F);
            bytes[1] = (byte) (((dc & 0xF) << 4) + ((pod >> 8) & 0xF));
            bytes[2] = (byte) (pod & 0xFF);
            bytes[3] = (byte) ((leaf >> 4) & 0xFF);
            bytes[4] = (byte) (((leaf & 0xF) << 4) + ((h >> 8) & 0xF));
            bytes[2] = (byte) (h & 0xFF);
            MacAddress eth = new MacAddress(bytes);
            MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF});
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(h + 1));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }

        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(hashSelector(lfRadixDown + 1, lfRadixUp, entry));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(500)
                .build();
        flowRuleService.applyFlowRules(flowRule);
    }

    // Todo: Proper ECMP algorithm based on incoming packets
    private PortNumber hashSelector(int portStart, int portCount, SwitchEntry entry) {
        return PortNumber.portNumber(portStart + (int)(Math.random() * portCount));
    }

    private class InternalDeviceListener implements DeviceListener {
        @Override
        public void event(DeviceEvent deviceEvent) {
            switch (deviceEvent.type()) {
                case DEVICE_ADDED:
                case DEVICE_UPDATED:
                    setupFlows(deviceEvent.subject());
                    break;
                case DEVICE_REMOVED:
                case DEVICE_SUSPENDED:
                default:
                    break;
            }
        }
    }
}
