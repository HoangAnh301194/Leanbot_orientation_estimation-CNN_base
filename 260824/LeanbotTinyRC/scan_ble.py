"""
Script quet va tim kiem tat ca thiet bi Bluetooth BLE xung quanh.
Dung de tim ten va ID chinh xac cua Leanbot.
"""

import asyncio
from bleak import BleakScanner


async def scan():
    print("\n[SCAN] Dang tim kiem thiet bi Bluetooth BLE trong 5 giay...")
    devices = await BleakScanner.discover(timeout=5.0)
    print(f"[KET QUA] Tim thay {len(devices)} thiet bi:\n")
    
    leanbots = []
    for d in devices:
        name = d.name if d.name else "Unknown"
        print(f"  - Name: '{name}' | MAC: {d.address}")
        if "leanbot" in name.lower():
            leanbots.append((name, d.address))
            
    print("-" * 60)
    if leanbots:
        print("===> CAC LEANBOT DUOC TIM THAY:")
        for name, addr in leanbots:
            print(f"     * {name}  (MAC: {addr})")
        print("\n=> Ban lay so ID trong ten Leanbot o tren de truyen vao --ble <ID>")
    else:
        print("[NOTE] Khong tim thay thiet bi nao co ten 'Leanbot'.")
        print("       - Vui long bat nguon Leanbot (cong tac ON).")
        print("       - Kiem tra pin va Bluetooth tren may tinh.")
    print("-" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(scan())
