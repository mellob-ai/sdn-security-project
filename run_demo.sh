#!/bin/bash
# ==============================================================
# SDN Security Project - Demo Runner
# ==============================================================
# This script runs the complete SDN security demonstration.
# It launches the controller, starts the network, and guides
# you through the demo steps.
#
# Run with: sudo bash run_demo.sh
# ==============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║   SDN TRAFFIC MONITORING & SECURITY PROTECTION         ║"
    echo "║               LIVE DEMONSTRATION                       ║"
    echo "║                                                        ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

wait_for_enter() {
    echo ""
    echo -e "${YELLOW}  Press ENTER to continue...${NC}"
    read -r
}

cleanup() {
    echo ""
    echo -e "${YELLOW}[CLEANUP] Stopping all components...${NC}"
    # Kill Ryu controller if running
    pkill -f "ryu-manager" 2>/dev/null || true
    pkill -f "ryu.cmd.manager" 2>/dev/null || true
    # Clean up Mininet
    mn -c 2>/dev/null || true
    echo -e "${GREEN}[CLEANUP] Done.${NC}"
}

# Trap to clean up on exit
trap cleanup EXIT

# ==============================================================
# Pre-checks
# ==============================================================
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (sudo).${NC}"
    echo "Usage: sudo bash run_demo.sh"
    exit 1
fi

print_banner

echo -e "${BLUE}[PRE-CHECK]${NC} Verifying components..."
echo ""

# Check components
READY=true

if python3 -c "from mininet.net import Mininet" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Mininet"
else
    echo -e "  ${RED}✗${NC} Mininet - Run setup_project.sh first!"
    READY=false
fi

if python3 -c "from ryu.base import app_manager" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Ryu Controller"
else
    echo -e "  ${RED}✗${NC} Ryu Controller - Run setup_project.sh first!"
    READY=false
fi

if command -v ovs-vsctl &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Open vSwitch"
else
    echo -e "  ${RED}✗${NC} Open vSwitch - Run setup_project.sh first!"
    READY=false
fi

if [ "$READY" = false ]; then
    echo ""
    echo -e "${RED}Some components are missing. Run:${NC}"
    echo "  sudo bash setup_project.sh"
    exit 1
fi

echo ""
echo -e "  ${GREEN}All components ready!${NC}"

# ==============================================================
# STEP 0: Clean up any previous runs
# ==============================================================
echo ""
echo -e "${BLUE}[STEP 0]${NC} Cleaning up previous sessions..."
pkill -f "ryu-manager" 2>/dev/null || true
pkill -f "ryu.cmd.manager" 2>/dev/null || true
mn -c 2>/dev/null || true

# Start OVS service
systemctl start ovs-vswitchd.service 2>/dev/null || \
    systemctl start openvswitch.service 2>/dev/null || true

echo -e "  ${GREEN}✓${NC} Cleanup complete"

# ==============================================================
# STEP 1: Start Ryu SDN Controller
# ==============================================================
print_banner

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  STEP 1: Starting the SDN Controller                   ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  The Ryu SDN controller is the 'brain' of the network."
echo "  It will:"
echo "    • Forward packets like a network switch"
echo "    • Monitor traffic statistics every 5 seconds"
echo "    • Detect if any host sends too much traffic"
echo "    • Automatically block attackers"
echo ""
echo -e "${BLUE}  Starting controller in background...${NC}"

# Determine ryu-manager command
if command -v ryu-manager &>/dev/null; then
    RYU_CMD="ryu-manager"
else
    RYU_CMD="python3 -m ryu.cmd.manager"
fi

# Start Ryu in background, log to file
$RYU_CMD "$SCRIPT_DIR/sdn_controller.py" \
    --ofp-tcp-listen-port 6633 \
    > "$SCRIPT_DIR/controller.log" 2>&1 &

RYU_PID=$!
echo "  Controller PID: $RYU_PID"

# Wait for controller to be ready
echo -e "  Waiting for controller to start..."
sleep 3

if kill -0 $RYU_PID 2>/dev/null; then
    echo -e "  ${GREEN}✓ SDN Controller is running!${NC}"
else
    echo -e "  ${RED}✗ Controller failed to start. Check controller.log${NC}"
    cat "$SCRIPT_DIR/controller.log"
    exit 1
fi

wait_for_enter

# ==============================================================
# STEP 2: Start Mininet Network
# ==============================================================
print_banner

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  STEP 2: Starting the Network                          ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  The network has 3 hosts and 1 switch:"
echo ""
echo "    h1 (10.0.0.1) ─── [Switch s1] ─── h2 (10.0.0.2)"
echo "                          │"
echo "                    h3 (10.0.0.3)"
echo "                      [ATTACKER]"
echo ""
echo "  The switch is controlled by the Ryu controller."
echo ""
echo -e "${YELLOW}  The Mininet CLI will open. Follow the demo steps below.${NC}"
echo ""
echo -e "${BOLD}  ═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  DEMO STEPS (run these commands in Mininet CLI):${NC}"
echo -e "${BOLD}  ═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Step A: Test normal connectivity${NC}"
echo "    mininet> pingall"
echo "    mininet> h1 ping -c 5 h2"
echo ""
echo -e "  ${GREEN}Step B: Generate normal traffic${NC}"
echo "    mininet> h1 python3 $SCRIPT_DIR/normal_traffic.py 10.0.0.2 20 &"
echo ""
echo -e "  ${GREEN}Step C: Launch attack from h3${NC}"
echo "    mininet> h3 python3 $SCRIPT_DIR/attack_traffic.py 10.0.0.1 30 &"
echo ""
echo -e "  ${GREEN}Step D: Watch the controller terminal for ALERT${NC}"
echo "    (Open a new terminal: tail -f $SCRIPT_DIR/controller.log)"
echo ""
echo -e "  ${GREEN}Step E: Verify h3 is blocked${NC}"
echo "    mininet> h3 ping -c 3 h1"
echo "    (Should show 100% packet loss - h3 is blocked!)"
echo ""
echo -e "  ${GREEN}Step F: Verify h1 and h2 still work${NC}"
echo "    mininet> h1 ping -c 3 h2"
echo "    (Should still work - only attacker is blocked)"
echo ""
echo -e "  Type 'exit' in Mininet to end the demo."
echo ""
echo -e "${YELLOW}  TIP: Open another terminal and run:${NC}"
echo -e "${YELLOW}    tail -f $SCRIPT_DIR/controller.log${NC}"
echo -e "${YELLOW}  to watch the controller detect attacks in real-time!${NC}"
echo ""

wait_for_enter

# Launch Mininet
echo -e "${BLUE}  Launching Mininet...${NC}"
echo ""
python3 "$SCRIPT_DIR/topology.py"

# ==============================================================
# Demo Complete
# ==============================================================
print_banner

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   DEMO COMPLETE! ✓                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Controller log saved to: $SCRIPT_DIR/controller.log"
echo ""
echo "  You can review the detection logs with:"
echo "    cat $SCRIPT_DIR/controller.log | grep ALERT"
echo ""
echo "  Thank you for watching the demonstration!"
echo ""
