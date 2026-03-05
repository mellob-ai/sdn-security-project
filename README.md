# Traffic Monitoring and Security Protection of Cloud Computing Network using Software Defined Networking (SDN)

## Project Overview

This project demonstrates an **SDN-based security monitoring system** that can detect and automatically block network attacks in real time.

### Architecture

```
┌─────────────────────────────────────────────────┐
│              SDN CONTROLLER (Ryu)               │
│  ┌───────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Learning  │ │ Traffic  │ │   Attack      │  │
│  │ Switch    │ │ Monitor  │ │   Detector    │  │
│  │           │ │ (5s poll)│ │   & Blocker   │  │
│  └───────────┘ └──────────┘ └───────────────┘  │
│                OpenFlow 1.3                     │
└────────────────────┬────────────────────────────┘
                     │ Control Channel
              ┌──────┴──────┐
              │  Switch s1  │
              │  (OVS)      │
              └──┬───┬───┬──┘
                 │   │   │
         ┌───────┘   │   └───────┐
         │           │           │
    ┌────┴───┐  ┌────┴───┐  ┌───┴────┐
    │   h1   │  │   h2   │  │   h3   │
    │10.0.0.1│  │10.0.0.2│  │10.0.0.3│
    │ Normal │  │ Normal │  │Attacker│
    └────────┘  └────────┘  └────────┘
```

### How It Works

1. **Network Setup**: Mininet creates a virtual network with 3 hosts and 1 switch
2. **Controller**: The Ryu controller manages the switch using OpenFlow
3. **Monitoring**: Every 5 seconds, the controller checks traffic statistics
4. **Detection**: If a host sends more than 50 packets/interval, it's flagged
5. **Blocking**: The controller installs a DROP rule on the switch to block the attacker

---

## Quick Start

### 1. Install Dependencies

```bash
sudo bash setup_project.sh
```

### 2. Run the Demo

```bash
sudo bash run_demo.sh
```

### 3. Manual Step-by-Step

**Terminal 1 — Start the controller:**
```bash
ryu-manager sdn_controller.py --ofp-tcp-listen-port 6633
```

**Terminal 2 — Start the network:**
```bash
sudo python3 topology.py
```

**Terminal 2 (Mininet CLI) — Demo commands:**
```bash
# Step A: Test connectivity
pingall

# Step B: Normal traffic (h1 pings h2)
h1 python3 normal_traffic.py 10.0.0.2 20 &

# Step C: Attack! (h3 floods h1)
h3 python3 attack_traffic.py 10.0.0.1 30 &

# Step D: Verify h3 is blocked
h3 ping -c 3 h1     # Should FAIL (blocked)

# Step E: Verify h1-h2 still works
h1 ping -c 3 h2     # Should SUCCEED
```

---

## File Structure

| File | Description |
|---|---|
| `setup_project.sh` | Installs all dependencies (run once) |
| `run_demo.sh` | Runs the complete demo with guided steps |
| `topology.py` | Creates the Mininet network (3 hosts, 1 switch) |
| `sdn_controller.py` | Ryu controller with monitoring and attack detection |
| `normal_traffic.py` | Generates normal ping traffic |
| `attack_traffic.py` | Simulates a DoS attack (ping flood) |

---

## Concepts for Presentation

### What is Software Defined Networking (SDN)?

Traditional networks have their control logic built into each switch/router. **SDN separates the control logic from the hardware**:

- **Data Plane** (switches): Forwards packets based on rules
- **Control Plane** (controller): Makes decisions about how packets should be forwarded

This separation allows us to **program the network** from a central controller, making it easier to add security features like automatic attack detection.

### What is Mininet?

Mininet is a **network emulator** that creates a realistic virtual network on your computer. It creates:
- Virtual hosts (like real computers)
- Virtual switches (using Open vSwitch)
- Virtual links between them

Everything runs on one machine, but behaves like a real network.

### What is the SDN Controller (Ryu)?

Ryu is a **Python-based SDN controller framework**. In our project, it:
1. **Receives** OpenFlow messages from the switch
2. **Decides** how traffic should be forwarded
3. **Installs flow rules** on the switch to control traffic
4. **Monitors statistics** to detect anomalies

### How Does Attack Detection Work?

Our detection uses **threshold-based monitoring**:

1. Every 5 seconds, the controller asks the switch: "How much traffic has passed through each port?"
2. The controller calculates the **change** (delta) since the last check
3. If any port shows more than **50 packets** or **50,000 bytes** in 5 seconds, it triggers an alert
4. The controller identifies which host is sending the excessive traffic
5. It installs a **DROP rule** on the switch that blocks all traffic from that host

This is a simplified version of real-world **anomaly detection** used in SDN security.

### What is Open vSwitch (OVS)?

Open vSwitch is a **virtual switch** that supports the **OpenFlow protocol**. It:
- Forwards packets between hosts based on **flow rules**
- Can be programmed by the SDN controller
- Supports features like VLAN, QoS, and flow statistics

### What is a Flow Rule?

A flow rule tells the switch what to do with specific traffic:

| Match (IF) | Action (THEN) |
|---|---|
| Source IP = 10.0.0.3 | DROP (block) |
| Destination MAC = 00:00:00:00:00:02 | Forward to port 2 |
| Source MAC = any | Send to controller |

The controller dynamically installs these rules based on traffic analysis.

---

## Detection Thresholds

These can be adjusted in `sdn_controller.py`:

| Parameter | Value | Meaning |
|---|---|---|
| `MONITOR_INTERVAL` | 5 seconds | How often to check traffic |
| `PACKET_THRESHOLD` | 50 packets | Max packets per interval before alert |
| `BYTE_THRESHOLD` | 50,000 bytes | Max bytes per interval before alert |
| `BLOCK_DURATION` | 300 seconds | How long to block an attacker |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Controller not connecting" | Make sure Ryu is running before starting Mininet |
| "Permission denied" | Run with `sudo` |
| "OVS not running" | `sudo systemctl start openvswitch` |
| "Module not found: ryu" | Run `setup_project.sh` again |
| "pingall fails" | Wait 5 seconds for controller to learn MACs, then retry |

---

## Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.x | Programming language |
| Mininet | Latest | Network simulation |
| Ryu | Latest | SDN controller framework |
| Open vSwitch | Latest | Virtual OpenFlow switch |
| OpenFlow | 1.3 | Protocol between controller and switch |
