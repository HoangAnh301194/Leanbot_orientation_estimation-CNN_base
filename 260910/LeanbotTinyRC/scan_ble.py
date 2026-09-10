"""
Script to scan and discover all nearby Bluetooth BLE devices.
Used to find the exact name and ID of the Leanbot.
"""

import asyncio
from bleak import BleakScanner


async def scan():
    print("\n[SCAN] Scanning for Bluetooth BLE devices for 5 seconds...")
    devices = await BleakScanner.discover(timeout=5.0)
    print(f"[RESULT] Found {len(devices)} device(s):\n")
    
    leanbots = []
    for d in devices:
        name = d.name if d.name else "Unknown"
        print(f"  - Name: '{name}' | MAC: {d.address}")
        if "leanbot" in name.lower():
            leanbots.append((name, d.address))
            
    print("-" * 60)
    if leanbots:
        print("===> LEANBOT DEVICES FOUND:")
        for name, addr in leanbots:
            print(f"     * {name}  (MAC: {addr})")
        print("\n=> Use the numeric ID from the Leanbot name above with --ble <ID>")
    else:
        print("[NOTE] No device with name 'Leanbot' was found.")
        print("       - Please power on the Leanbot (switch to ON).")
        print("       - Check battery and Bluetooth on your computer.")
    print("-" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(scan())
