#!/bin/bash
# ==============================================================
# SDN Security Project - Setup Script
# ==============================================================
# This script installs all required dependencies for the
# SDN Traffic Monitoring & Security Protection project.
#
# Run with: sudo bash setup_project.sh
# ==============================================================

set -e  # Stop on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[STEP $1]${NC} $2"
}

print_ok() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_fail() {
    echo -e "${RED}  ✗ $1${NC}"
}

# ==============================================================
# Check if running as root
# ==============================================================
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (sudo).${NC}"
    echo "Usage: sudo bash setup_project.sh"
    exit 1
fi

print_header "SDN SECURITY PROJECT - SETUP"

echo "This script will install:"
echo "  1. Python pip        - Python package manager"
echo "  2. Open vSwitch      - Virtual network switch"
echo "  3. Mininet           - Network simulator"
echo "  4. Ryu Controller    - SDN controller framework"
echo ""
echo "System: $(uname -r)"
echo "Python: $(python3 --version 2>&1)"
echo ""

# Detect package manager
if command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    PKG_INSTALL="pacman -S --noconfirm --needed"
    PKG_UPDATE="pacman -Sy"
elif command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    PKG_INSTALL="apt install -y"
    PKG_UPDATE="apt update"
else
    echo -e "${RED}ERROR: Unsupported package manager. Need pacman or apt.${NC}"
    exit 1
fi

echo "Package manager: $PKG_MANAGER"
echo ""

# ==============================================================
# STEP 1: Update system packages
# ==============================================================
print_header "STEP 1: Updating System Packages"

echo "What: Refreshing package database to get latest versions."
echo "Why:  Ensures we install the correct, up-to-date packages."
echo ""

$PKG_UPDATE
print_ok "Package database updated"

# ==============================================================
# STEP 2: Install Python pip
# ==============================================================
print_header "STEP 2: Installing Python pip"

echo "What: pip is the Python package installer."
echo "Why:  We need it to install the Ryu SDN controller."
echo ""

if [ "$PKG_MANAGER" = "pacman" ]; then
    $PKG_INSTALL python-pip
else
    $PKG_INSTALL python3-pip
fi

# Verify
if python3 -m pip --version &> /dev/null; then
    print_ok "pip installed: $(python3 -m pip --version 2>&1)"
else
    print_fail "pip installation failed!"
    exit 1
fi

# ==============================================================
# STEP 3: Install Open vSwitch
# ==============================================================
print_header "STEP 3: Installing Open vSwitch"

echo "What: Open vSwitch (OVS) is a virtual network switch that"
echo "      supports the OpenFlow protocol."
echo "Why:  Mininet uses OVS to create virtual switches that the"
echo "      SDN controller can program with flow rules."
echo ""

if [ "$PKG_MANAGER" = "pacman" ]; then
    $PKG_INSTALL openvswitch
else
    $PKG_INSTALL openvswitch-switch openvswitch-common
fi

# Start OVS service
if command -v systemctl &> /dev/null; then
    systemctl enable --now ovs-vswitchd.service 2>/dev/null || true
    systemctl enable --now ovsdb-server.service 2>/dev/null || true
    systemctl enable --now openvswitch-switch.service 2>/dev/null || true
    systemctl enable --now openvswitch.service 2>/dev/null || true
fi

# Verify
if command -v ovs-vsctl &> /dev/null; then
    print_ok "Open vSwitch installed: $(ovs-vsctl --version | head -1)"
else
    print_fail "Open vSwitch installation failed!"
    exit 1
fi

# ==============================================================
# STEP 4: Install Mininet dependencies
# ==============================================================
print_header "STEP 4: Installing Mininet"

echo "What: Mininet creates realistic virtual networks on your"
echo "      computer. It simulates hosts, switches, and links."
echo "Why:  We need it to create the test network for our demo."
echo ""

# Install Mininet
if [ "$PKG_MANAGER" = "pacman" ]; then
    # Arch: build from source
    $PKG_INSTALL git base-devel net-tools iproute2 iputils iperf3 \
        python-setuptools help2man

    MININET_DIR="/tmp/mininet_build"
    if [ -d "$MININET_DIR" ]; then
        rm -rf "$MININET_DIR"
    fi

    echo ""
    print_step "4a" "Cloning Mininet from GitHub..."
    git clone https://github.com/mininet/mininet.git "$MININET_DIR"
    cd "$MININET_DIR"

    git checkout -b local_build $(git tag -l | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1) 2>/dev/null || true

    print_step "4b" "Installing Mininet Python package..."
    python3 setup.py install 2>/dev/null || pip install . 2>/dev/null || python3 -m pip install . 2>/dev/null
else
    # Ubuntu/Debian: install from apt (much simpler)
    $PKG_INSTALL mininet net-tools iproute2 iputils-ping iperf3
fi

# Verify
if python3 -c "from mininet.net import Mininet; print('Mininet OK')" 2>/dev/null; then
    print_ok "Mininet installed successfully"
else
    # Fallback: try pip install
    print_warn "Trying pip install as fallback..."
    python3 -m pip install mininet --break-system-packages 2>/dev/null || true
    if python3 -c "from mininet.net import Mininet; print('Mininet OK')" 2>/dev/null; then
        print_ok "Mininet installed via pip"
    else
        print_fail "Mininet installation failed. You may need to install manually."
    fi
fi

cd "$SCRIPT_DIR"

# ==============================================================
# STEP 5: Install Ryu SDN Controller
# ==============================================================
print_header "STEP 5: Installing Ryu SDN Controller"

echo "What: Ryu is an SDN controller framework written in Python."
echo "      It receives OpenFlow messages from switches and can"
echo "      program flow rules on them."
echo "Why:  This is the 'brain' of our SDN system that monitors"
echo "      traffic and blocks attackers."
echo ""

# Try ryu-controller (modern maintained fork) first, then os-ken, then original ryu
RYU_INSTALLED=false

# First try: ryu-controller (maintained fork, Python 3.12+ compatible)
print_step "5a" "Trying ryu-controller (modern fork)..."
if python3 -m pip install ryu-controller --break-system-packages 2>/dev/null; then
    if python3 -c "from ryu.base import app_manager" 2>/dev/null; then
        print_ok "ryu-controller installed"
        RYU_INSTALLED=true
    fi
fi

# Second try: os-ken (official successor, uses os_ken namespace)
if [ "$RYU_INSTALLED" = false ]; then
    print_step "5b" "Trying os-ken (official Ryu successor)..."
    if python3 -m pip install os-ken --break-system-packages 2>/dev/null; then
        if python3 -c "from os_ken.base import app_manager" 2>/dev/null; then
            print_ok "os-ken installed"
            RYU_INSTALLED=true
        fi
    fi
fi

# Third try: original ryu (may not work on Python 3.12+)
if [ "$RYU_INSTALLED" = false ]; then
    print_step "5c" "Trying original ryu package..."
    python3 -m pip install ryu --break-system-packages 2>/dev/null || true
    if python3 -c "from ryu.base import app_manager" 2>/dev/null; then
        print_ok "ryu installed"
        RYU_INSTALLED=true
    fi
fi

if [ "$RYU_INSTALLED" = false ]; then
    print_fail "Could not install Ryu controller."
    print_warn "You may need to install it in a Python virtual environment."
    print_warn "Try: python3 -m venv venv && source venv/bin/activate && pip install ryu"
fi

# Verify ryu-manager or osken-manager command
if command -v ryu-manager &> /dev/null; then
    print_ok "ryu-manager command available"
elif command -v osken-manager &> /dev/null; then
    print_ok "osken-manager command available"
else
    print_warn "ryu-manager/osken-manager not in PATH. You can use:"
    print_warn "python3 -m os_ken.cmd.manager sdn_controller.py"
fi

# ==============================================================
# STEP 6: Install additional Python packages
# ==============================================================
print_header "STEP 6: Installing Additional Python Packages"

python3 -m pip install eventlet msgpack --break-system-packages 2>/dev/null || true
print_ok "Additional packages installed"

# ==============================================================
# STEP 7: Make scripts executable
# ==============================================================
print_header "STEP 7: Setting File Permissions"

chmod +x "$SCRIPT_DIR/run_demo.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/setup_project.sh" 2>/dev/null || true
print_ok "Scripts marked as executable"

# ==============================================================
# VERIFICATION SUMMARY
# ==============================================================
print_header "INSTALLATION SUMMARY"

echo "Checking all components..."
echo ""

# Check each component
check_component() {
    local name="$1"
    local check_cmd="$2"
    if eval "$check_cmd" &> /dev/null; then
        print_ok "$name"
        return 0
    else
        print_fail "$name"
        return 1
    fi
}

ERRORS=0

check_component "Python 3          " "python3 --version" || ((ERRORS++))
check_component "pip               " "python3 -m pip --version" || ((ERRORS++))
check_component "Open vSwitch      " "ovs-vsctl --version" || ((ERRORS++))
check_component "Mininet           " "python3 -c 'from mininet.net import Mininet'" || ((ERRORS++))
check_component "Ryu Controller    " "python3 -c 'from ryu.base import app_manager' || python3 -c 'from os_ken.base import app_manager'" || ((ERRORS++))

echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  ALL COMPONENTS INSTALLED SUCCESSFULLY! ✓${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo "  Next step: Run the demo with:"
    echo "    sudo bash run_demo.sh"
    echo ""
else
    echo -e "${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}  $ERRORS component(s) may need manual attention.${NC}"
    echo -e "${YELLOW}============================================================${NC}"
    echo ""
    echo "  Try running the failed installations manually."
    echo "  See INSTALLATION.md for detailed instructions."
fi
