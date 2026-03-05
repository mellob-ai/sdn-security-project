#!/usr/bin/env python3
"""
SDN Security Demo - Network Topology
=====================================
Creates a simple Mininet network with:
  - 1 OpenFlow switch (s1)
  - 3 hosts: h1 (10.0.0.1), h2 (10.0.0.2), h3 (10.0.0.3)
  - Connected to Ryu SDN controller on port 6633

h1 and h2 are normal users, h3 is the simulated attacker.

Usage:
    sudo python3 topology.py
"""

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def create_topology():
    """Create and start the SDN demo network."""

    info("*** Creating SDN Security Demo Network ***\n")

    # Create network with a remote controller (Ryu)
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
    )

    # Add the Ryu controller
    info("*** Adding Ryu SDN Controller\n")
    controller = net.addController(
        "ryu_controller",
        controller=RemoteController,
        ip="127.0.0.1",
        port=6633,
    )

    # Add the OpenFlow switch
    info("*** Adding OpenFlow Switch\n")
    switch = net.addSwitch("s1", protocols="OpenFlow13")

    # Add hosts
    info("*** Adding Hosts\n")
    h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
    h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
    h3 = net.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")

    # Create links (connect hosts to switch)
    info("*** Creating Links\n")
    net.addLink(h1, switch, bw=10)  # 10 Mbps bandwidth
    net.addLink(h2, switch, bw=10)
    net.addLink(h3, switch, bw=10)

    # Start the network
    info("*** Starting Network\n")
    net.start()

    # Print network information
    info("\n")
    info("=" * 60 + "\n")
    info("  SDN SECURITY DEMO NETWORK\n")
    info("=" * 60 + "\n")
    info("  Network Topology:\n")
    info("    h1 (10.0.0.1) --- [s1] --- h2 (10.0.0.2)\n")
    info("                       |                      \n")
    info("                     h3 (10.0.0.3) [ATTACKER] \n")
    info("\n")
    info("  Controller: Ryu @ 127.0.0.1:6633\n")
    info("  Switch: s1 (OpenFlow 1.3)\n")
    info("=" * 60 + "\n")
    info("\n")
    info("  Quick Commands:\n")
    info("    h1 ping h2          - Normal ping test\n")
    info("    h3 ping -f h1       - Flood ping (attack simulation)\n")
    info("    pingall             - Test all connectivity\n")
    info("    dpctl dump-flows    - View flow rules on switch\n")
    info("\n")

    # Test connectivity
    info("*** Testing initial connectivity\n")
    net.pingAll()

    # Start CLI for interactive use
    info("\n*** Starting Mininet CLI (type 'exit' to stop)\n")
    CLI(net)

    # Cleanup
    info("*** Stopping Network\n")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    create_topology()
