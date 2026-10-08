import socket
import logging
import subprocess
import re

logger = logging.getLogger(__name__)

ESP32_KNOWN_MAC = "d0-cf-13-07-bb-84"
ESP32_MAC_PREFIX = "d0-cf-13"


def discover_esp32_ip(fallback_ip: str) -> str:
    """Auto-detect current ESP32 IP from ARP table by its unique MAC address."""
    # 1. Quick ping fallback_ip
    try:
        ret = subprocess.run(
            ["ping", "-n", "1", "-w", "150", fallback_ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if ret.returncode == 0:
            return fallback_ip
    except Exception:
        pass

    # 2. Check current ARP cache
    try:
        arp_output = subprocess.check_output("arp -a", shell=True).decode("utf-8", errors="ignore")
        for line in arp_output.splitlines():
            line_clean = line.lower().replace(":", "-")
            if ESP32_MAC_PREFIX in line_clean:
                m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                if m:
                    detected_ip = m.group(1)
                    logger.info("[Auto-Discovery] Detected ESP32 at IP %s (MAC: %s)", detected_ip, ESP32_KNOWN_MAC)
                    print(f"[*] Auto-Discovery: Phat hien ESP32 tai IP moi: {detected_ip}")
                    return detected_ip
    except Exception:
        pass

    return fallback_ip


class UDPClient:
    def __init__(self, host: str, port: int):
        self.host = discover_esp32_ip(host)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Minimize buffer size to eliminate OS transmit queueing delay
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        except Exception:
            pass
        self.sock.setblocking(False)

    def send(self, data: bytes):
        """Send packet to ESP32."""
        try:
            self.sock.sendto(data, (self.host, self.port))
        except Exception as e:
            logger.error("Failed to send UDP packet to %s:%d: %s", self.host, self.port, e)

    def close(self):
        """Close socket."""
        try:
            self.sock.close()
        except Exception:
            pass
