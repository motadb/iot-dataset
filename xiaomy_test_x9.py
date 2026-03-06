#!/usr/bin/env python3
import asyncio
from bleak import BleakScanner

# Marca do manufacturer data da Xiaomi
XIAOMI_MANUF = 0xFE95

def parse_xiaomi(data: bytes):
    """
    Procura o frame 0x10 0x04 (LYWSD03 style) e devolve (temp, hum, batt) se encontrado.
    temp em graus C, hum em %, batt em %
    """
    if not data:
        return None
    temp = hum = batt = None
    i = 0
    while i < len(data):
        dtype = data[i]
        if dtype == 0x10 and i+1 < len(data):  # Temperature
            length = data[i+1]
            if i+2+length <= len(data):
                temp_raw = int.from_bytes(data[i+2:i+2+length], "little", signed=True)
                temp = temp_raw / 10.0
                i += 2 + length
            else:
                i += 1
        elif dtype == 0x06 and i+1 < len(data):  # Humidity
            length = data[i+1]
            if i+2+length <= len(data):
                hum_raw = int.from_bytes(data[i+2:i+2+length], "little")
                hum = hum_raw / 10.0
                i += 2 + length
            else:
                i += 1
        elif dtype == 0x04 and i+1 < len(data):  # Battery
            length = data[i+1]
            if i+2+length <= len(data):
                batt = data[i+2]
                i += 2 + length
            else:
                i += 1
        else:
            i += 1
    if temp is not None or hum is not None or batt is not None:
        return (temp, hum, batt)
    return None

async def read_sensor_characteristics(mac):
    from bleak import BleakClient
    print(f"Conectando ao sensor {mac} para ler characteristics...")
    try:
        async with BleakClient(mac) as client:
            # Tenta ler a characteristic típica de temp/hum (0x000a ou similar)
            # Endereço pode variar, mas 0x000a é comum
            # Tenta alguns UUIDs conhecidos
            uuids = [
                "00002a6e-0000-1000-8000-00805f9b34fb", # Temperature
                "00002a6f-0000-1000-8000-00805f9b34fb", # Humidity
                "00002a19-0000-1000-8000-00805f9b34fb", # Battery
                "0000000a-0000-1000-8000-00805f9b34fb", # Custom
            ]
            for uuid in uuids:
                try:
                    value = await client.read_gatt_char(uuid)
                    print(f"  Characteristic {uuid}: {value.hex()} ({value})")
                except Exception as e:
                    print(f"  Não foi possível ler {uuid}: {e}")
    except Exception as e:
        print(f"Erro ao conectar ao sensor: {e}")

def detection_callback(device, advertisement_data):
    # Mostra debug completo apenas para o sensor alvo
    if device.address.upper() == "A4:C1:38:85:5E:41":
        print(f"DEBUG SENSOR MAC: {device.address} | RSSI: {device.rssi}")
        if advertisement_data.service_data:
            for uuid, svc_data in advertisement_data.service_data.items():
                print(f"  service_data {uuid}: {svc_data.hex()}")
        if advertisement_data.manufacturer_data:
            for manuf_id, data in advertisement_data.manufacturer_data.items():
                print(f"  manufacturer_data {manuf_id:#06x}: {data.hex()}")
        # Tenta conectar e ler characteristics (apenas uma vez por execução)
        # Para evitar múltiplas conexões, pode-se usar uma flag global
        global already_read
        if not already_read:
            already_read = True
            asyncio.create_task(read_sensor_characteristics(device.address))


already_read = False

async def run():
    global already_read
    already_read = False
    scanner = BleakScanner(detection_callback)
    print("A escuta dos anúncios BLE (Xiaomi LYWSD03)... Ctrl+C para sair")
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(3600)  # fica a correr; imprime via callback
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Parando scanner...")
    finally:
        await scanner.stop()

if __name__ == "__main__":
    asyncio.run(run())
