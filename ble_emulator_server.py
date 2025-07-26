# /// script
# dependencies = [
#   "bumble==0.0.212",
#   "uvicorn==0.35.0",
#   "fastapi==0.115.14"
# ]
# ///

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from bumble.att import ATT_INSUFFICIENT_ENCRYPTION_ERROR, ATT_Error
from bumble.device import Connection, Device, DeviceConfiguration
from bumble.gatt import (
    GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
    GATT_DEVICE_INFORMATION_SERVICE,
    GATT_MANUFACTURER_NAME_STRING_CHARACTERISTIC,
    Characteristic,
    CharacteristicValue,
    Descriptor,
    Service,
)
from bumble.transport import open_transport_or_link
from bumble.transport.common import Transport
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

if sys.platform.startswith("win"):
    adb_executable = "adb.exe"
else:
    adb_executable = "adb"

ADB_PATH = Path(os.environ["ANDROID_HOME"]) / "platform-tools" / adb_executable

if not ADB_PATH.exists():
    raise FileNotFoundError(
        f"ADB executable not found at {ADB_PATH}. Please set the ANDROID_HOME environment variable correctly."
    )


def call_adb(command: list[str]) -> str:
    try:
        result = subprocess.run(
            [ADB_PATH] + command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error_output = exc.stderr or exc.stdout or str(exc)
        raise Exception(f"ADB command failed: {error_output}") from exc


app = FastAPI()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/ping/")
async def ping():
    return "pong"


@app.post("/grant_permission/")
async def grant_permission(package: str, permission: str):
    call_adb(["shell", "pm", "grant", package, permission])


@app.post("/revoke_permission/")
async def revoke_permission(package: str, permission: str):
    call_adb(["shell", "pm", "revoke", package, permission])


@app.post("/activate_bluetooth/")
async def activate_bluetooth():
    btle_status = call_adb(["shell", "settings", "get", "global", "bluetooth_on"])
    print(f"{btle_status=}")
    if btle_status == "0":
        # Enable Bluetooth (A small hack with key events)
        call_adb(["shell", "am", "start", "-a", "android.settings.BLUETOOTH_SETTINGS"])
        call_adb(["shell", "input", "keyevent", "19"])  # Arrow up
        call_adb(["shell", "input", "keyevent", "23"])  # Enter


class Listener(Device.Listener, Connection.Listener):
    def __init__(self, device):
        self.device = device

    def on_connection(self, connection):
        logging.info(f"=== Connected to {connection}")
        connection.listener = self

    def on_disconnection(self, reason):
        logging.info(f"### Disconnected, reason={reason}")


def my_custom_read(connection):
    logging.info("----- READ from", connection)
    return bytes(f"Hello {connection}", "ascii")


def my_custom_write(connection, value):
    logging.info(f"----- WRITE from {connection}: {value}")


def my_custom_read_with_error(connection):
    logging.info("----- READ from", connection, "[returning error]")
    if connection.is_encrypted:
        return bytes([123])

    raise ATT_Error(ATT_INSUFFICIENT_ENCRYPTION_ERROR)


def my_custom_write_with_error(connection, value):
    logging.info(f"----- WRITE from {connection}: {value}", "[returning error]")
    if not connection.is_encrypted:
        raise ATT_Error(ATT_INSUFFICIENT_ENCRYPTION_ERROR)


global_hci_transport: Transport | Exception | None = None


async def gatt_server_task():
    global global_hci_transport

    try:
        logging.info("<<< connecting to HCI...")
        async with await open_transport_or_link("android-netsim") as hci_transport:
            logging.info("<<< connected")

            # Store the transport globally for use in the listener
            global_hci_transport = hci_transport

            # Create a device to manage the host
            device = Device.from_config_with_hci(
                DeviceConfiguration.from_dict(
                    {
                        "name": "Bumble",
                        "address": "F0:F1:F2:F3:F4:F5",
                        "advertising_interval": 2000,
                        "keystore": "JsonKeyStore",
                        "irk": "865F81FF5A8B486EAAE29A27AD9F77DC",
                    }
                ),
                hci_transport.source,
                hci_transport.sink,
            )
            device.listener = Listener(device)

            # Add a few entries to the device's GATT server
            descriptor = Descriptor(
                GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
                Descriptor.READABLE,
                "My Description".encode(),
            )
            manufacturer_name_characteristic = Characteristic(
                GATT_MANUFACTURER_NAME_STRING_CHARACTERISTIC,
                Characteristic.Properties.READ,
                Characteristic.READABLE,
                "Fitbit".encode(),
                [descriptor],
            )
            device_info_service = Service(
                GATT_DEVICE_INFORMATION_SERVICE, [manufacturer_name_characteristic]
            )
            custom_service1 = Service(
                "50DB505C-8AC4-4738-8448-3B1D9CC09CC5",
                [
                    Characteristic(
                        "D901B45B-4916-412E-ACCA-376ECB603B2C",
                        Characteristic.Properties.READ
                        | Characteristic.Properties.WRITE,
                        Characteristic.READABLE | Characteristic.WRITEABLE,
                        CharacteristicValue(read=my_custom_read, write=my_custom_write),
                    ),
                    Characteristic(
                        "552957FB-CF1F-4A31-9535-E78847E1A714",
                        Characteristic.Properties.READ
                        | Characteristic.Properties.WRITE,
                        Characteristic.READABLE | Characteristic.WRITEABLE,
                        CharacteristicValue(
                            read=my_custom_read_with_error,
                            write=my_custom_write_with_error,
                        ),
                    ),
                    Characteristic(
                        "486F64C6-4B5F-4B3B-8AFF-EDE134A8446A",
                        Characteristic.Properties.READ
                        | Characteristic.Properties.NOTIFY,
                        Characteristic.READABLE,
                        bytes("hello", "utf-8"),
                    ),
                ],
            )
            device.add_services([device_info_service, custom_service1])

            # Debug print
            for attribute in device.gatt_server.attributes:
                logging.info(attribute)

            # Get things going
            await device.power_on()

            # Connect to a peer
            await device.start_advertising(auto_restart=True)

            await hci_transport.source.wait_for_termination()
    except Exception as e:
        logging.error(f"Error in GATT server task: {e}")
        global_hci_transport = e


@app.post("/gatt_server/start/")
async def gatt_server_start():
    if global_hci_transport is None:
        asyncio.create_task(gatt_server_task())

        # wait for the global_hci_transport to be set
        while global_hci_transport is None:
            await asyncio.sleep(0.1)

        if isinstance(global_hci_transport, Exception):
            return JSONResponse(
                status_code=500,
                content={
                    "status": "GATT server failed",
                    "error": str(global_hci_transport),
                },
            )
        else:
            return JSONResponse(
                status_code=200,
                content={"status": "GATT server task started"},
            )
    else:
        raise RuntimeError("GATT server task is already running")


@app.post("/gatt_server/status/")
async def gatt_server_status():
    if global_hci_transport is None:
        return JSONResponse(
            status_code=503,
            content={"status": "GATT server not running"},
        )
    elif isinstance(global_hci_transport, Exception):
        return JSONResponse(
            status_code=500,
            content={
                "status": "GATT server failed",
                "error": str(global_hci_transport),
            },
        )
    else:
        return JSONResponse(
            status_code=200,
            content={"status": "GATT server running"},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "emulator_controller_server:app", host="127.0.0.1", port=8000, reload=True
    )
