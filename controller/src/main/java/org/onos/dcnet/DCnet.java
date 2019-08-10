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
import com.google.common.collect.ImmutableList;
import com.google.common.collect.SetMultimap;
import org.apache.felix.scr.annotations.Activate;
import org.apache.felix.scr.annotations.Component;
import org.apache.felix.scr.annotations.Deactivate;
import org.apache.felix.scr.annotations.Reference;
import org.apache.felix.scr.annotations.ReferenceCardinality;
import org.onlab.packet.*;
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
import org.onosproject.net.flow.criteria.IPCriterion;
import org.onosproject.net.flowobjective.FlowObjectiveService;
import org.onosproject.net.group.*;
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

/**
 * ONOS App implementing DCnet forwarding scheme
 */
@Component(immediate = true)
public class DCnet {
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
        private String idmac;

        public HostEntry(String name, String leaf, String port, String rmac, String idmac) {
            this.name = name;
            this.leaf = leaf;
            this.port = port;
            this.rmac = rmac;
            this.idmac = idmac;
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

        public String getIdmac() {
            return this.idmac;
        }

    }

    private static Logger log = LoggerFactory.getLogger(DCnet.class);

    private static final String configLoc = "/home/reed226/DCnet/";

    private static final int DC = 0;
    private static final int SUPER = 1;
    private static final int SPINE = 2;
    private static final int LEAF = 3;
    private static final int BASE_PRIO = 50000;

    private int dcCount;
    private int dcRadixDown;
    private int ssRadixDown;
    private int spRadixUp;
    private int spRadixDown;
    private int lfRadixUp;
    private int lfRadixDown;

    private List<GroupBucket> leafBuckets = new ArrayList<>();
    private List<GroupBucket> spineBuckets = new ArrayList<>();
    private List<GroupBucket> dcBuckets = new ArrayList<>();

    /* Maps Chassis ID to a switch entry */
    private Map<String, SwitchEntry> switchDB = new TreeMap<>();

    /* Maps IP address to a host entry */
    private Map<String, HostEntry> hostDB = new TreeMap<>();

    /* List of currently active flow rules */
    private List<FlowRule> installedFlows = new ArrayList<>();

    private ApplicationId appId;

    protected static KryoNamespace appKryo = new KryoNamespace.Builder()
            .register(Integer.class)
            .register(DeviceId.class)
            .build("group-fwd-app");

    private final SetMultimap<GroupKey, FlowRule> pendingFlows = HashMultimap.create();

    private final DeviceListener deviceListener = new InternalDeviceListener();

    private final HostListener hostListener = new InternalHostListener();

    private final PacketProcessor packetProcessor = new LeafPacketProcessor();

    /* Selector for IPv4 traffic to intercept */
    private final TrafficSelector intercept = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4).build();

    /* Initializes application by reading configuration files for hosts, switches, and topology design */
    private void init() {

        switchDB = new TreeMap<>();
        hostDB = new TreeMap<>();

        try {
            /* Setup switch database by reading fields in switch configuration file */
            BufferedReader switchConfig = new BufferedReader(new FileReader(configLoc + "switch_config.csv"));
            String line;
            switchConfig.readLine();
            while ((line = switchConfig.readLine()) != null) {
                String[] config = line.split(",");
                switchDB.put(config[0], new SwitchEntry(config[1], Integer.parseInt(config[2]),
                                                        Integer.parseInt(config[3]), Integer.parseInt(config[4]),
                                                        Integer.parseInt(config[5])));
            }
            switchConfig.close();

            /* Setup host database by reading fields in host configuration file */
            BufferedReader hostConfig = new BufferedReader(new FileReader(configLoc + "host_config.csv"));
            hostConfig.readLine();
            while ((line = hostConfig.readLine()) != null) {
                String[] config = line.split(",");
                hostDB.put(config[0], new HostEntry(config[1], config[2], config[3], config[4], config[5]));
            }
            hostConfig.close();

            /* Setup topology specifications by reading fields in topology configuration file */
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
            topConfig.close();

            for(int i = 1; i <= lfRadixUp; i++) {
                TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(lfRadixDown + i));
                leafBuckets.add(DefaultGroupBucket.createSelectGroupBucket(treatment.build()));
            }
            for(int i = 1; i <= spRadixUp; i++) {
                TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(spRadixDown + i));
                spineBuckets.add(DefaultGroupBucket.createSelectGroupBucket(treatment.build()));
            }
            for(int i = 1; i <= dcRadixDown; i++) {
                TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(i));
                dcBuckets.add(DefaultGroupBucket.createSelectGroupBucket(treatment.build()));
            }
        }

        catch (IOException e) {
            e.printStackTrace();
        }
    }

    /* Allows application to be started by ONOS controller */
    @Activate
    public void activate() {

        init();
        appId = coreService.registerApplication("org.onosproject.dcnet");
        packetService.addProcessor(packetProcessor, BASE_PRIO);
        packetService.requestPackets(intercept, PacketPriority.CONTROL, appId, Optional.empty());
        deviceService.addListener(deviceListener);
        //hostService.addListener(hostListener);
        log.info("Started");
    }

    /* Allows application to be stopped by ONOS controller */
    @Deactivate
    public void deactivate() {

        packetService.removeProcessor(packetProcessor);
        flowRuleService.removeFlowRulesById(appId);
        deviceService.removeListener(deviceListener);
        //hostService.removeListener(hostListener);
        log.info("Stopped");
    }

    /* Helper function to translate int version of IP (used by ONOS) into String (used in this application) */
    private String integerToIpStr(int ip) {
        return String.format("%d.%d.%d.%d", (ip >> 24) & 0xFF, (ip >> 16) & 0xFF, (ip >> 8) & 0xFF, ip & 0xFF);
    }

    /* Helper function to translate String version of MAC (used in this application) into byte[] (used by ONOS) */
    private MacAddress strToMac(String address) {

        byte[] bytes = new byte[6];
        String[] octets = address.split(":");
        for (int i = 0; i < 6; i++) {
            bytes[i] = (byte)(Integer.parseInt(octets[i], 16));
        }
        return new MacAddress(bytes);
    }

    /* Creates rules for packets with new IPv4 destination that a leaf switch receives */
    private void processPacket(PacketContext context, Ethernet eth) {

        /* Check that packet should be translated by sending device */
        IPv4 ip;
        if (eth.getEtherType() == Ethernet.TYPE_IPV4) {
            ip = (IPv4) (eth.getPayload());
        }
        else {
            return;
        }
        log.info(eth.getDestinationMAC().toString());
        Device device = deviceService.getDevice(context.inPacket().receivedFrom().deviceId());
        String id = device.chassisId().toString();
        SwitchEntry entry = switchDB.get(id);
        if (entry.getLevel() != LEAF) {
            return;
        }
        int ip_dst = ip.getDestinationAddress();
        log.info(integerToIpStr(ip_dst));
        HostEntry host = hostDB.get(integerToIpStr(ip_dst));
        if (host == null) {
            return;
        }

        /* Obtain location information from RMAC address corresponding to IP destination */
        String[] bytes = host.getRmac().split(":");
        int dc = Integer.parseInt(bytes[0], 16) * 16 + Integer.parseInt(bytes[1].substring(0, 1), 16);
        int pod = Integer.parseInt(bytes[1].substring(1), 16) * 16 + Integer.parseInt(bytes[2], 16);
        int leaf = Integer.parseInt(bytes[3], 16) * 16 + Integer.parseInt(bytes[4].substring(0, 1), 16);
        TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4).matchIPDst(IpPrefix.valueOf(ip_dst, 32));

        /* If recipient is directly connected to leaf, translate ethernet destination back to recipients's and forward to it */
        if (dc == entry.getDc() && pod == entry.getPod() && leaf == entry.getLeaf()) {
            int port = Integer.parseInt(bytes[4].substring(1), 16) * 16 + Integer.parseInt(bytes[5], 16) + 1;
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setEthDst(strToMac(host.getIdmac())).setOutput(PortNumber.portNumber(port));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
            installedFlows.add(flowRule);
        }

        /* If recipient is connected to another leaf, translate ethernet destination to RMAC and forward to spines */
        else {
            GroupKey key = new DefaultGroupKey(appKryo.serialize(Objects.hash(device)));
            GroupDescription groupDescription = new DefaultGroupDescription(device.id(), GroupDescription.Type.SELECT, new GroupBuckets(leafBuckets), key, BASE_PRIO + LEAF, appId);
            groupService.addGroup(groupDescription);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setEthDst(strToMac(host.getRmac())).group(new GroupId(BASE_PRIO + LEAF));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 500)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
            installedFlows.add(flowRule);
        }
    }

    /* Intercepts packets sent to controller */
    private class LeafPacketProcessor implements PacketProcessor {
        @Override
        public void process(PacketContext context) {
            Ethernet eth = context.inPacket().parsed();
            processPacket(context, eth);
        }
    }

    /* Initializes flow rules for switch based on its level in topology */
    private synchronized void setupFlows(Device device) {

        String id = device.chassisId().toString();
        log.info("Chassis " + id + " connected");
        if (switchDB.containsKey(id)) {
            SwitchEntry entry = switchDB.get(id);
            log.info("Switch " + id + " connected");
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

    /* Adds flows for data center switch to forward down to super spines and towards other data center switches */
    private void addFlowsDC(Device device) {

        String id = device.chassisId().toString();
        SwitchEntry entry = switchDB.get(id);

        /* Add rule to ECMP packets belonging in this data center towards super spines */
        int dc = entry.getDc();
        byte[] bytes = new byte[6];
        bytes[0] = (byte)((dc >> 4) & 0x3F);
        bytes[1] = (byte)((dc & 0xF) << 4);
        MacAddress eth = new MacAddress(bytes);
        MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xF0, 0x00, 0x00, 0x00, 0x00});
        TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask).matchEthType(Ethernet.TYPE_IPV4);
        GroupKey key = new DefaultGroupKey(appKryo.serialize(Objects.hash(device)));
        GroupDescription groupDescription = new DefaultGroupDescription(device.id(), GroupDescription.Type.SELECT, new GroupBuckets(dcBuckets), key, BASE_PRIO + DC, appId);
        groupService.addGroup(groupDescription);
        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().group(new GroupId(BASE_PRIO + DC));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withSelector(selector.build())
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(BASE_PRIO + 1000)
                .build();
        flowRuleService.applyFlowRules(flowRule);

        /* Add rules to forward packets belonging to another data center to the correct one */
        for (int d = 0; d < dcCount; d++) {
            int port = d;
            if (d > dc) {
                port--;
            }
            else if (d == dc) {
                continue;
            }
            bytes = new byte[6];
            bytes[0] = (byte)((d >> 4) & 0x3F);
            bytes[1] = (byte)((d & 0xF) << 4);
            eth = new MacAddress(bytes);
            selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask).matchEthType(Ethernet.TYPE_IPV4);
            treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(dcRadixDown + port + 1));
            flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 500)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }
        // TODO: Forward all other traffic to internet
    }

    /* Adds flows for super spine switches to forward down to spines and up to the data center switch */
    private void addFlowsSuper(Device device) {

        String id = device.chassisId().toString();
        SwitchEntry entry = switchDB.get(id);
        int dc = entry.getDc();

        /* Add rules to forward packets belonging in this data center down towards the correct spine based on pod destination */
        for (int p = 0; p < ssRadixDown; p++) {
            byte[] bytes = new byte[6];
            bytes[0] = (byte) ((dc >> 4) & 0x3F);
            bytes[1] = (byte) (((dc & 0xF) << 4) + ((p >> 8) & 0xF));
            bytes[2] = (byte) (p & 0xFF);
            MacAddress eth = new MacAddress(bytes);
            MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xFF, (byte) 0xFF, 0x00, 0x00, 0x00});
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask).matchEthType(Ethernet.TYPE_IPV4);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(p + 1));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }

        /* Add rule to forward packets belonging to another data center up to the data center switch */
        TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4);
        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(ssRadixDown + 1));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withSelector(selector.build())
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(BASE_PRIO + 500)
                .build();
        flowRuleService.applyFlowRules(flowRule);
    }

    /* Adds flows for spine switches to forward down to leaves and up to super spines */
    private void addFlowsSpine(Device device) {
        String id = device.chassisId().toString();
        SwitchEntry entry = switchDB.get(id);
        int dc = entry.getDc();
        int pod = entry.getPod();

        /* Add rules to forward packets belonging in this pod down towards the correct leaf based on ToR destination */
        for (int l = 0; l < spRadixDown; l++) {
            byte[] bytes = new byte[6];
            bytes[0] = (byte) ((dc >> 4) & 0x3F);
            bytes[1] = (byte) (((dc & 0xF) << 4) + ((pod >> 8) & 0xF));
            bytes[2] = (byte) (pod & 0xFF);
            bytes[3] = (byte) ((l >> 4) & 0xFF);
            bytes[4] = (byte) ((l & 0xF) << 4);
            MacAddress eth = new MacAddress(bytes);
            MacAddress mask = new MacAddress(new byte[]{(byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xFF, (byte) 0xF0, 0x00});
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthDstMasked(eth, mask).matchEthType(Ethernet.TYPE_IPV4);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().setOutput(PortNumber.portNumber(l + 1));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 1000)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }

        /* Add rule to ECMP packets belonging to another pod up to super spines */
        TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4);
        GroupKey key = new DefaultGroupKey(appKryo.serialize(Objects.hash(device)));
        GroupDescription groupDescription = new DefaultGroupDescription(device.id(), GroupDescription.Type.SELECT, new GroupBuckets(spineBuckets), key, BASE_PRIO + SPINE, appId);
        groupService.addGroup(groupDescription);
        TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().group(new GroupId(BASE_PRIO + SPINE));
        FlowRule flowRule = DefaultFlowRule.builder()
                .fromApp(appId)
                .makePermanent()
                .withSelector(selector.build())
                .withTreatment(treatment.build())
                .forDevice(device.id())
                .withPriority(BASE_PRIO + 500)
                .build();
        flowRuleService.applyFlowRules(flowRule);
    }

    /* Adds default flows for leaf to hand all IPv4 packets to controller if it hasn't seen the IP destination before */
    private void addFlowsLeaf(Device device) {
        for (int h = 1; h <= lfRadixDown + lfRadixUp; h++) {
            TrafficSelector.Builder selector = DefaultTrafficSelector.builder().matchInPort(PortNumber.portNumber(h)).matchEthType(Ethernet.TYPE_IPV4);
            TrafficTreatment.Builder treatment = DefaultTrafficTreatment.builder().punt();
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selector.build())
                    .withTreatment(treatment.build())
                    .forDevice(device.id())
                    .withPriority(BASE_PRIO + 100)
                    .build();
            flowRuleService.applyFlowRules(flowRule);
        }
    }

    private void removeSwitch(Device device) {

    }

    /* Invalidate all flows using the IP address of a host that was moved */
    private void removeHostFlows(Host host) {
        Set<IpAddress> ips = host.ipAddresses();
        List<FlowRule> temp = new ArrayList<>(installedFlows);
        for (IpAddress ip : ips) {
            for (FlowRule flow : installedFlows) {
                if (((IPCriterion)flow.selector().getCriterion(Criterion.Type.IPV4_DST)).ip().address().equals(ip)) {
                    flowRuleService.removeFlowRules(flow);
                    temp.remove(flow);
                }
            }
        }
        installedFlows = temp;
    }

    /* Listen for switches that are added to topology */
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
                    removeSwitch(deviceEvent.subject());
                    break;
                default:
                    break;
            }
        }
    }

    /* Listed for hosts that are moved or removed from network */
    private class InternalHostListener implements HostListener {
        @Override
        public void event(HostEvent hostEvent) {
            switch (hostEvent.type()) {
                case HOST_MOVED:
                case HOST_REMOVED:
                    removeHostFlows(hostEvent.subject());
                    break;
                default:
                    break;
            }
        }
    }
}
