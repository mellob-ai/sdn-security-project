# Installation Guide

Step-by-step guide to install all components for the SDN Security Demo.

---

## System Requirements

| Requirement | Minimum |
|---|---|
| RAM | 2 GB free |
| Disk Space | 1 GB free |
| OS | Linux (any distribution) |
| Python | 3.8 or higher |
| Privileges | Root/sudo access required |

---

## Automatic Installation

Run this single command to install everything:

```bash
sudo bash setup_project.sh
```

If you prefer to install manually, follow the steps below.

---

## Manual Installation

### Step 1: Install Python pip

**What is it?** pip is the package installer for Python. It lets you install Python libraries.

**Why needed?** We use it to install the Ryu SDN controller and other Python packages.

**Arch/Garuda Linux:**
```bash
sudo pacman -S python-pip
```

**Ubuntu/Debian:**
```bash
sudo apt install python3-pip
```

**Verify:**
```bash
python3 -m pip --version
# Should show: pip 24.x.x from ...
```

---

### Step 2: Install Open vSwitch

**What is it?** Open vSwitch (OVS) is a virtual network switch that supports the OpenFlow protocol, which allows the SDN controller to program flow rules on it.

**Why needed?** Mininet uses OVS to create virtual switches that the SDN controller can control. Without OVS, we cannot simulate an SDN network.

**Arch/Garuda Linux:**
```bash
sudo pacman -S openvswitch
sudo systemctl enable --now openvswitch
```

**Ubuntu/Debian:**
```bash
sudo apt install openvswitch-switch
sudo systemctl enable --now openvswitch-switch
```

**Verify:**
```bash
ovs-vsctl --version
# Should show: ovs-vsctl (Open vSwitch) 3.x.x
```

---

### Step 3: Install Mininet

**What is it?** Mininet is a network emulator. It creates virtual hosts, switches, and links on your machine. The virtual network behaves like a real network, allowing us to test SDN applications without physical hardware.

**Why needed?** This is how we create the test network with 3 hosts and a switch for our demo.

**Install from source:**
```bash
# Install build dependencies
# Arch:
sudo pacman -S git base-devel net-tools iproute2 iputils iperf3 python-setuptools help2man
# Ubuntu:
# sudo apt install git build-essential net-tools iproute2 iputils-ping iperf3 python3-setuptools help2man

# Clone and install
git clone https://github.com/mininet/mininet.git /tmp/mininet_build
cd /tmp/mininet_build
sudo python3 setup.py install
# or: sudo pip install .
```

**Verify:**
```bash
python3 -c "from mininet.net import Mininet; print('Mininet OK')"
# Should print: Mininet OK
```

---

### Step 4: Install Ryu SDN Controller

**What is it?** Ryu is a framework for building SDN controller applications in Python. It handles the OpenFlow protocol communication with switches, letting us write Python code to control network behavior.

**Why needed?** This is the "brain" of our system — it monitors traffic, detects attacks, and installs blocking rules.

```bash
# Try the maintained fork first (Python 3.12+ compatible)
sudo pip install ryu-controller --break-system-packages

# If that doesn't work, try:
sudo pip install os-ken --break-system-packages

# If that doesn't work either:
sudo pip install ryu --break-system-packages
```

**Verify:**
```bash
python3 -c "from ryu.base import app_manager; print('Ryu OK')"
# Should print: Ryu OK

ryu-manager --version
# Should show version number
```

---

### Step 5: Install Supporting Packages

```bash
sudo pip install eventlet msgpack --break-system-packages
```

---

## Verify Everything Works

Run these commands to check all components:

```bash
echo "=== Checking Components ==="
python3 --version
python3 -m pip --version
ovs-vsctl --version
python3 -c "from mininet.net import Mininet; print('Mininet: OK')"
python3 -c "from ryu.base import app_manager; print('Ryu: OK')"
echo "=== All checks complete ==="
```

All lines should succeed without errors.

---

## Next Steps

After installation, run the demo:

```bash
sudo bash run_demo.sh
```

Or manually:

1. **Terminal 1:** `ryu-manager sdn_controller.py --ofp-tcp-listen-port 6633`
2. **Terminal 2:** `sudo python3 topology.py`
3. Follow the demo steps in the README.
