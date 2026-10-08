import os
import sys
import argparse
import time
import psutil

from desktop import config
from desktop.protocol import pack_reboot_bootloader
from desktop.network import UDPClient
from desktop.controller import KMController


def ensure_single_instance():
    """Terminate previous running KM Bridge instances to prevent hook collision."""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] != current_pid and proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline') or []
                cmd_str = ' '.join(cmdline)
                if 'desktop.main' in cmd_str:
                    print(f"[*] Found previous KMBridge instance (PID: {proc.info['pid']}). Terminating...")
                    proc.kill()
                    proc.wait(timeout=2.0)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass


def main():
    ensure_single_instance()
    parser = argparse.ArgumentParser(
        description="KM Bridge: Share Keyboard & Mouse with Laptop B via ESP32-S3 over Wi-Fi"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=config.ESP32_IP,
        help=f"ESP32-S3 IP address (default: {config.ESP32_IP})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.UDP_PORT,
        help=f"UDP Port (default: {config.UDP_PORT})"
    )
    parser.add_argument(
        "--reboot-bootloader",
        action="store_true",
        help="Send command to reboot ESP32-S3 into ROM Bootloader mode for re-flashing"
    )

    args = parser.parse_args()

    config.ESP32_IP = args.ip
    config.UDP_PORT = args.port

    if args.reboot_bootloader:
        print(f"[*] Sending reboot command to ESP32-S3 at {config.ESP32_IP}:{config.UDP_PORT}...")
        client = UDPClient(config.ESP32_IP, config.UDP_PORT)
        client.send(pack_reboot_bootloader())
        time.sleep(0.5)
        client.close()
        print("[+] Done! ESP32-S3 is now rebooting into ROM Download Mode.")
        print("[+] It will reappear as USB Serial / COM port for firmware flashing.")
        return

    controller = KMController()
    try:
        controller.start()
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()

