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

        public SwitchEntry(String name, int level, int dc, int pod, int leaf) {
            this.name = name;
            this.level = level;
            this.dc = dc;
            this.pod = pod;
            this.leaf = leaf;
            this.joined = false;
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

        public boolean isJoined() {
            return this.joined;
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

    private final HostListener hostListener = new InternalHostListener();

    private final DeviceListener deviceListener = new InternalDeviceListener();

    private final PacketProcessor packetProcessor = new PingPacketProcessor();

    // Selector for ICMP traffic that is to be intercepted
    private final TrafficSelector intercept = DefaultTrafficSelector.builder()
            .matchEthType(Ethernet.TYPE_IPV4).matchIPProtocol(IPv4.PROTOCOL_ICMP)
            .build();

    private void init() {
        switchDB = new TreeMap<>();
        hostDB = new TreeMap<>();

        try {
            BufferedReader switchConfig = new BufferedReader(new FileReader(configLoc + "switch_config.csv"));
            String line = switchConfig.readLine();
            while (!((line = switchConfig.readLine()).equals(""))) {
                String[] config = line.split(",");
                switchDB.put(config[0], new SwitchEntry(config[1], Integer.parseInt(config[2]),
                                                        Integer.parseInt(config[3]), Integer.parseInt(config[4]),
                                                        Integer.parseInt(config[5])));
            }

            BufferedReader hostConfig = new BufferedReader(new FileReader(configLoc + "host_config.csv"));
            line = hostConfig.readLine();
            while (!((line = hostConfig.readLine()).equals(""))) {
                String[] config = line.split(",");
                hostDB.put(config[0], new HostEntry(config[1], config[2], config[3], config[4]));
            }

            BufferedReader topConfig = new BufferedReader(new FileReader(configLoc + "top_config.csv"));
            line = topConfig.readLine();
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
        packetService.addProcessor(packetProcessor, 50000);
        packetService.requestPackets(intercept, PacketPriority.CONTROL, appId, Optional.empty());
        setupFlows();
        hostService.addListener(hostListener);
        deviceService.addListener(deviceListener);
        log.info("Started");
    }

    @Deactivate
    public void deactivate() {
        packetService.removeProcessor(packetProcessor);
        flowRuleService.removeFlowRulesById(appId);
        hostService.removeListener(hostListener);
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


    // Indicates whether the specified packet corresponds to ICMP ping.
    private boolean isIcmpPing(Ethernet eth) {
        return eth.getEtherType() == Ethernet.TYPE_IPV4 &&
                ((IPv4) eth.getPayload()).getProtocol() == IPv4.PROTOCOL_ICMP;
    }


    // Intercepts packets
    private class PingPacketProcessor implements PacketProcessor {
        @Override
        public void process(PacketContext context) {
            Ethernet eth = context.inPacket().parsed();
            processPacket(context, eth);
        }
    }

    private synchronized void setupFlows() {
        Set<Device> devices = Sets.newHashSet(deviceService.getAvailableDevices());
        devices.forEach(this::processHostFlows);
    }



    private void processHostFlows(Device device) {
        Set<Host> hosts = Sets.newHashSet(hostService.getHosts());

        hosts.forEach(host -> {

            TrafficSelector.Builder selectorBuilder = DefaultTrafficSelector.builder();
            TrafficTreatment.Builder treatmentBuilder = DefaultTrafficTreatment.builder();
            selectorBuilder.matchEthDst(host.mac());
            Integer groupId = 0;
            GroupKey groupKey = null;

            if (host.location().deviceId().equals(device.id())) {

            } else {

            }

            treatmentBuilder.deferred();
            treatmentBuilder.group(new GroupId(groupId));
            FlowRule flowRule = DefaultFlowRule.builder()
                    .fromApp(appId)
                    .makePermanent()
                    .withSelector(selectorBuilder.build())
                    .withTreatment(treatmentBuilder.build())
                    .forDevice(device.id())
                    .withPriority(50000)
                    .build();
            addPendingFlow(groupKey, flowRule);
        });
    }

    private void addPendingFlow(GroupKey groupkey, FlowRule flowRule) {
        synchronized (pendingFlows) {
            pendingFlows.put(groupkey, flowRule);
        }
    }



    private Set<FlowRule> fetchPendingFlows(GroupKey groupKey) {
        Set<FlowRule> flowRules;

        synchronized (pendingFlows) {
            flowRules = pendingFlows.removeAll(groupKey);
        }
        return flowRules;
    }

    private PortNumber getOutPortForDeviceLink(Device sourceDevice, Device targetDevice) {

        Set<Path> paths = pathService.getPaths(sourceDevice.id(), targetDevice.id());

        if (paths == null || paths.isEmpty()) {
            return null;
        }

        Path path = paths.iterator().next(); // use first path

        if (path.links().isEmpty()) {
            // XXX: will this happened ?
            return null;
        }

        // first link should contains devive+port -> device+port
        Link link = path.links().get(0);
        return link.src().port();
    }

    private class InternalHostListener implements HostListener {
        @Override
        public void event(HostEvent hostEvent) {
            switch (hostEvent.type()) {
                case HOST_ADDED:
                case HOST_UPDATED:
                    setupFlows();
                    break;
                case HOST_REMOVED:
                    break;
                default:
                    break;
            }

        }

    }

    private class InternalDeviceListener implements DeviceListener {
        @Override
        public void event(DeviceEvent deviceEvent) {
            switch (deviceEvent.type()) {
                case DEVICE_ADDED:
                case DEVICE_UPDATED:
                    setupFlows();
                    break;
                case DEVICE_REMOVED:
                case DEVICE_SUSPENDED:
                default:
                    break;
            }
        }
    }
}
