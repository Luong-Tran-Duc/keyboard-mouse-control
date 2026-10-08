"""Main entry point for KM Bridge Desktop Client."""

import sys
import argparse
import time

from desktop import config
from desktop.protocol import pack_reboot_bootloader
from desktop.network import UDPClient
from desktop.controller import KMController


def main():
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

