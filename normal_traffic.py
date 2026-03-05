#!/usr/bin/env python3
"""
Normal Traffic Generator
========================
Generates normal, low-rate ping traffic between hosts.
This simulates regular user activity on the network.

Usage (run inside Mininet CLI):
    mininet> h1 python3 normal_traffic.py h2 &
    mininet> h2 python3 normal_traffic.py h1 &

Or standalone (provide target IP):
    python3 normal_traffic.py 10.0.0.2
"""

import subprocess
import sys
import time
import os


def generate_normal_traffic(target_ip, duration=60, interval=1):
    """
    Generate normal ping traffic to the target IP.

    Args:
        target_ip: IP address to ping
        duration: How long to run (seconds)
        interval: Time between pings (seconds)
    """
    hostname = os.popen("hostname").read().strip()

    print(f"[NORMAL TRAFFIC] {hostname} -> {target_ip}")
    print(f"[NORMAL TRAFFIC] Duration: {duration}s, Interval: {interval}s")
    print(f"[NORMAL TRAFFIC] Rate: {1/interval:.1f} pings/second (NORMAL)")
    print("-" * 50)

    start_time = time.time()
    ping_count = 0

    try:
        while time.time() - start_time < duration:
            ping_count += 1
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", target_ip],
                capture_output=True,
                text=True,
            )

            elapsed = time.time() - start_time
            if result.returncode == 0:
                # Extract RTT from ping output
                rtt_line = [
                    line for line in result.stdout.split("\n") if "time=" in line
                ]
                rtt = rtt_line[0].split("time=")[1] if rtt_line else "N/A"
                print(
                    f"  [{elapsed:6.1f}s] Ping #{ping_count} to {target_ip}: "
                    f"OK (rtt={rtt})"
                )
            else:
                print(
                    f"  [{elapsed:6.1f}s] Ping #{ping_count} to {target_ip}: "
                    f"FAILED (host unreachable or blocked)"
                )

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[NORMAL TRAFFIC] Stopped by user.")

    print("-" * 50)
    print(f"[NORMAL TRAFFIC] Completed. Sent {ping_count} pings in {duration}s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 normal_traffic.py <target_ip> [duration] [interval]")
        print("Example: python3 normal_traffic.py 10.0.0.2 60 1")
        sys.exit(1)

    target = sys.argv[1]
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    intv = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

    generate_normal_traffic(target, duration=dur, interval=intv)
