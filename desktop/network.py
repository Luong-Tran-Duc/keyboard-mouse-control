import socket
import logging
import subprocess
import re
import concurrent.futures

logger = logging.getLogger(__name__)

ESP32_KNOWN_MAC = "d0-cf-13-07-bb-84"
ESP32_MAC_PREFIX = "d0-cf-13"


def _extract_ip_by_mac_prefix(prefix: str) -> str | None:
    """Read ARP table and find IP matching MAC prefix."""
    try:
        arp_output = subprocess.check_output("arp -a", shell=True).decode("utf-8", errors="ignore")
        for line in arp_output.splitlines():
            line_clean = line.lower().replace(":", "-")
            if prefix in line_clean:
                m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def discover_esp32_ip(fallback_ip: str) -> str:
    """Auto-detect current ESP32 IP from ARP table by its unique hardware MAC address."""
    # 1. Check existing ARP table first
    detected = _extract_ip_by_mac_prefix(ESP32_MAC_PREFIX)
    if detected:
        logger.info("[Auto-Discovery] Detected ESP32 at IP %s (MAC: %s)", detected, ESP32_KNOWN_MAC)
        print(f"[*] Auto-Discovery: Phat hien ESP32 tai IP: {detected} (MAC: {ESP32_KNOWN_MAC})")
        return detected

    # 2. Try pinging fallback IP to see if its ARP entry appears
    if fallback_ip:
        try:
            subprocess.run(["ping", "-n", "1", "-w", "150", fallback_ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            detected = _extract_ip_by_mac_prefix(ESP32_MAC_PREFIX)
            if detected:
                print(f"[*] Auto-Discovery: Phat hien ESP32 tai IP: {detected}")
                return detected
        except Exception:
            pass

    # 3. Active subnet ARP scan (ping sweep local subnet to populate ARP cache)
    try:
        def quick_ping(ip):
            subprocess.run(["ping", "-n", "1", "-w", "60", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subnet_prefix = fallback_ip.rsplit('.', 1)[0] if fallback_ip else "192.168.1"
        target_ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            list(executor.map(quick_ping, target_ips))

        detected = _extract_ip_by_mac_prefix(ESP32_MAC_PREFIX)
        if detected:
            print(f"[*] Auto-Discovery: Quet subnet phat hien ESP32 tai IP: {detected}")
            return detected
    except Exception:
        pass

    print(f"[!] Warning: Khong tim thay MAC ESP32 trong ARP table, su dung fallback: {fallback_ip}")
    return fallback_ip


class UDPClient:
    def __init__(self, host: str, port: int):
        self.host = discover_esp32_ip(host)
        self.port = port
        self.broadcast_ip = "192.168.1.255"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Enable broadcasting for critical control packets
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass

        # Minimize buffer size to eliminate OS transmit queueing delay
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        except Exception:
            pass
        self.sock.setblocking(False)

    def send(self, data: bytes):
        """Send packet to ESP32 (unicast + broadcast for critical state packets)."""
        try:
            self.sock.sendto(data, (self.host, self.port))
            # Critical mode switch / reboot commands are also broadcast to ensure zero packet loss
            if data and data[0] in (0xFE, 0xFF, 0xAA):
                self.sock.sendto(data, (self.broadcast_ip, self.port))
        except Exception as e:
            logger.error("Failed to send UDP packet: %s", e)

    def close(self):
        """Close socket."""
        try:
            self.sock.close()
        except Exception:
            pass
