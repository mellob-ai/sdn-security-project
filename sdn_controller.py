#!/usr/bin/env python3
"""
SDN Security Controller - Traffic Monitor & Attack Detector
============================================================
Ryu SDN controller application that:
  1. Acts as a learning switch (forwards traffic normally)
  2. Monitors traffic statistics every 5 seconds
  3. Detects abnormal traffic using threshold-based logic
  4. Automatically blocks malicious hosts by installing drop rules

Usage:
    ryu-manager sdn_controller.py
"""

# Compatibility: support both 'ryu' and 'os-ken' (its maintained successor)
try:
    from ryu.base import app_manager
    from ryu.controller import ofp_event
    from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
    from ryu.ofproto import ofproto_v1_3
    from ryu.lib.packet import packet, ethernet, arp, ipv4, icmp
    from ryu.lib import hub
except ImportError:
    from os_ken.base import app_manager
    from os_ken.controller import ofp_event
    from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
    from os_ken.ofproto import ofproto_v1_3
    from os_ken.lib.packet import packet, ethernet, arp, ipv4, icmp
    from os_ken.lib import hub
from datetime import datetime

# ============================================================
# CONFIGURATION - Adjust these thresholds for your demo
# ============================================================
MONITOR_INTERVAL = 5       # Check traffic every 5 seconds
PACKET_THRESHOLD = 50      # Packets per interval to trigger alert
BYTE_THRESHOLD = 50000     # Bytes per interval to trigger alert
BLOCK_DURATION = 300       # Block attacker for 300 seconds (5 min)
# ============================================================


class SDNSecurityController(app_manager.RyuApp):
    """
    SDN Security Controller - Monitors traffic and blocks attacks.

    This controller:
    - Learns MAC addresses to forward traffic (like a smart switch)
    - Polls traffic statistics from the switch every few seconds
    - Detects when traffic from a host exceeds safe thresholds
    - Installs flow rules to DROP traffic from attackers
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNSecurityController, self).__init__(*args, **kwargs)

        # MAC address table: {dpid: {mac: port}}
        self.mac_to_port = {}

        # Traffic statistics tracking: {dpid: {port: {packets, bytes}}}
        self.prev_stats = {}

        # Set of blocked IPs
        self.blocked_hosts = set()

        # IP to MAC mapping (learned from packets)
        self.ip_to_mac = {}

        # IP to port mapping
        self.ip_to_port = {}

        # Connected datapaths (switches)
        self._datapaths = {}

        # Start the traffic monitoring thread
        self.monitor_thread = hub.spawn(self._monitor_loop)

        self._log("=" * 60)
        self._log("  SDN SECURITY CONTROLLER STARTED")
        self._log("=" * 60)
        self._log(f"  Monitor interval : {MONITOR_INTERVAL}s")
        self._log(f"  Packet threshold : {PACKET_THRESHOLD} pkts/interval")
        self._log(f"  Byte threshold   : {BYTE_THRESHOLD} bytes/interval")
        self._log(f"  Block duration   : {BLOCK_DURATION}s")
        self._log("=" * 60)

    # ----------------------------------------------------------
    # Logging helper
    # ----------------------------------------------------------
    def _log(self, message, level="INFO"):
        """Print a timestamped log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}", flush=True)

    # ----------------------------------------------------------
    # Switch setup - called when a switch connects
    # ----------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        Called when a switch first connects to the controller.
        Installs a default 'table-miss' flow that sends unknown
        packets to the controller for processing.
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Track this datapath for stats requests
        self._datapaths[datapath.id] = datapath

        self._log(f"Switch connected: dpid={datapath.id}")

        # Install table-miss flow entry
        # This tells the switch: "if no rule matches, send to controller"
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
            )
        ]
        self._add_flow(datapath, 0, match, actions)
        self._log(f"Table-miss flow installed on switch {datapath.id}")

    # ----------------------------------------------------------
    # Packet handler - learning switch + IP tracking
    # ----------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Called when a packet arrives at the controller.
        Implements learning switch logic and tracks IP-MAC mappings.
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]
        dpid = datapath.id

        # Parse the packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        src_mac = eth.src
        dst_mac = eth.dst

        # Initialize MAC table for this switch
        self.mac_to_port.setdefault(dpid, {})

        # Learn the source MAC address
        self.mac_to_port[dpid][src_mac] = in_port

        # Learn IP-to-MAC mapping from IP packets
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip = ip_pkt.src
            self.ip_to_mac[src_ip] = src_mac
            self.ip_to_port[src_ip] = in_port

            # Check if this IP is blocked
            if src_ip in self.blocked_hosts:
                self._log(
                    f"Dropped packet from BLOCKED host {src_ip}",
                    level="BLOCK",
                )
                return

        # Learn from ARP packets too
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self.ip_to_mac[arp_pkt.src_ip] = src_mac
            self.ip_to_port[arp_pkt.src_ip] = in_port

        # Determine output port
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install a flow rule to avoid future packet-in for known paths
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=src_mac)
            self._add_flow(datapath, 1, match, actions)

        # Send the packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    # ----------------------------------------------------------
    # Flow rule helper
    # ----------------------------------------------------------
    def _add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        """Install a flow rule on the switch."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        datapath.send_msg(mod)

    # ----------------------------------------------------------
    # Traffic monitoring loop
    # ----------------------------------------------------------
    def _monitor_loop(self):
        """Periodically request traffic statistics from switches."""
        while True:
            hub.sleep(MONITOR_INTERVAL)
            # Request stats from all connected switches
            for dpid in list(self._datapaths.keys()):
                self._request_stats(dpid)

    def _request_stats(self, dpid):
        """Send a stats request to the switch."""
        if dpid in self._datapaths:
            datapath = self._datapaths[dpid]
            parser = datapath.ofproto_parser

            # Request port statistics
            req = parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
            datapath.send_msg(req)

    # ----------------------------------------------------------
    # Stats reply handler - ATTACK DETECTION LOGIC
    # ----------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        """
        Called when the switch responds with port statistics.
        This is where we detect abnormal traffic!
        """
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self._log("-" * 50, level="MONITOR")
        self._log(
            f"{'Port':<8} {'RX Pkts':<12} {'RX Bytes':<14} "
            f"{'Δ Pkts':<10} {'Δ Bytes':<12} {'Status':<10}",
            level="MONITOR",
        )
        self._log("-" * 50, level="MONITOR")

        self.prev_stats.setdefault(dpid, {})

        for stat in sorted(body, key=lambda s: s.port_no):
            port_no = stat.port_no

            # Skip the LOCAL port (controller port)
            if port_no > 1000:
                continue

            rx_packets = stat.rx_packets
            rx_bytes = stat.rx_bytes

            # Calculate delta (change since last check)
            prev = self.prev_stats[dpid].get(port_no, {"packets": 0, "bytes": 0})
            delta_packets = rx_packets - prev["packets"]
            delta_bytes = rx_bytes - prev["bytes"]

            # Update stored stats
            self.prev_stats[dpid][port_no] = {
                "packets": rx_packets,
                "bytes": rx_bytes,
            }

            # Skip first reading (no previous data to compare)
            if prev["packets"] == 0 and prev["bytes"] == 0:
                status = "INIT"
            elif delta_packets > PACKET_THRESHOLD or delta_bytes > BYTE_THRESHOLD:
                status = "⚠ ALERT"
                self._handle_attack(datapath, port_no, delta_packets, delta_bytes)
            else:
                status = "✓ OK"

            self._log(
                f"{port_no:<8} {rx_packets:<12} {rx_bytes:<14} "
                f"{delta_packets:<10} {delta_bytes:<12} {status:<10}",
                level="MONITOR",
            )

        self._log("-" * 50, level="MONITOR")

    # ----------------------------------------------------------
    # Attack response - BLOCK THE ATTACKER
    # ----------------------------------------------------------
    def _handle_attack(self, datapath, port_no, delta_packets, delta_bytes):
        """
        Respond to a detected attack:
        1. Identify the attacker's IP from the port
        2. Log a clear alert message
        3. Install a DROP flow rule to block the attacker
        """
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Find the IP address connected to this port
        attacker_ip = None
        attacker_mac = None
        for ip, port in self.ip_to_port.items():
            if port == port_no:
                attacker_ip = ip
                attacker_mac = self.ip_to_mac.get(ip)
                break

        if attacker_ip is None:
            self._log(
                f"High traffic on port {port_no} ({delta_packets} pkts, "
                f"{delta_bytes} bytes) - source IP unknown yet",
                level="WARNING",
            )
            return

        if attacker_ip in self.blocked_hosts:
            return  # Already blocked

        # === ALERT ===
        self._log("!" * 60, level="ALERT")
        self._log(
            f"  🚨 ATTACK DETECTED FROM {attacker_ip} (MAC: {attacker_mac})",
            level="ALERT",
        )
        self._log(
            f"  Traffic rate: {delta_packets} packets, {delta_bytes} bytes "
            f"in last {MONITOR_INTERVAL}s",
            level="ALERT",
        )
        self._log(
            f"  Threshold exceeded: packets>{PACKET_THRESHOLD} or "
            f"bytes>{BYTE_THRESHOLD}",
            level="ALERT",
        )
        self._log("!" * 60, level="ALERT")

        # === BLOCK THE ATTACKER ===
        self._log(
            f"  🛡️  BLOCKING all traffic from {attacker_ip} "
            f"for {BLOCK_DURATION} seconds...",
            level="ACTION",
        )

        # Install DROP rule: match on attacker's MAC, no actions = DROP
        if attacker_mac:
            match = parser.OFPMatch(eth_src=attacker_mac)
            # Priority 100 = higher than normal forwarding rules
            # Empty actions list = DROP the packet
            self._add_flow(
                datapath,
                priority=100,
                match=match,
                actions=[],  # No actions = DROP
                hard_timeout=BLOCK_DURATION,
            )

        # Also block by IP if available
        match_ip = parser.OFPMatch(
            eth_type=0x0800,  # IPv4
            ipv4_src=attacker_ip,
        )
        self._add_flow(
            datapath,
            priority=100,
            match=match_ip,
            actions=[],  # DROP
            hard_timeout=BLOCK_DURATION,
        )

        self.blocked_hosts.add(attacker_ip)

        self._log(
            f"  ✅ Flow rules installed. {attacker_ip} is now BLOCKED.",
            level="ACTION",
        )
        self._log(
            f"  ℹ️  Block will auto-expire in {BLOCK_DURATION} seconds.",
            level="INFO",
        )
        self._log(
            f"  Currently blocked hosts: {self.blocked_hosts}",
            level="INFO",
        )
