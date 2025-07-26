import abc
import asyncio
import dataclasses
import logging
from typing import override
from uuid import uuid4

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
from bumble.host import Host
from bumble.transport import open_transport
from bumble.transport.common import Transport


class BlePeripheralDatabase:
    def __init__(self):
        self.db: dict[str, BlePeripheral] = {}

    def add_peripheral(self, peripheral: "BlePeripheral") -> str:
        peripheral_id = str(uuid4())
        self.db[peripheral_id] = peripheral
        return peripheral_id

    async def stop_peripheral(self, peripheral_id: str):
        peripheral = self.db[peripheral_id]
        assert peripheral.transport
        assert peripheral.wait_task

        peripheral.wait_task.cancel()
        await peripheral.transport.close()

        del self.db[peripheral_id]

    async def stop_all(self):
        for peripheral_id, peripheral in list(self.db.items()):
            await self.stop_peripheral(peripheral_id)


class Listener(Device.Listener, Connection.Listener):
    def __init__(self, device):
        self.device = device

    def on_connection(self, connection):
        print(f"=== Connected to {connection}")
        connection.listener = self

    def on_disconnection(self, reason):
        print(f"### Disconnected, reason={reason}")


@dataclasses.dataclass
class BlePeripheral:
    def __init__(self):
        self.transport: Transport | None = None
        self.wait_task: asyncio.Task | None = None

    async def start_peripheral(self):
        """
        Peripheral starten
        """
        print("Opening transport")
        self.transport = await open_transport("android-netsim")

        print("Creating device")
        device = self.create_device()

        print("Power device on")
        await device.power_on()

        print("Start advertising")
        await device.start_advertising(auto_restart=True)

        self.wait_task = asyncio.create_task(
            self.transport.source.wait_for_termination()  # type: ignore
        )

    @abc.abstractmethod
    def create_device(self) -> Device: ...


class BlePeripheral1(BlePeripheral):
    def __init__(self, name: str, address: str):
        super().__init__()
        self.name = name
        self.address = address

    @override
    def create_device(self) -> Device:
        assert self.transport

        config = DeviceConfiguration.from_dict(
            {
                "name": self.name,
                "address": self.address,
                "advertising_interval": 2000,
                "keystore": "JsonKeyStore",
                "irk": "865F81FF5A8B486EAAE29A27AD9F77DC",
            }
        )
        device = Device(
            config=config, host=Host(self.transport.source, self.transport.sink)
        )

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
                    Characteristic.Properties.READ | Characteristic.Properties.WRITE,
                    Characteristic.READABLE | Characteristic.WRITEABLE,
                    CharacteristicValue(
                        read=self.my_custom_read, write=self.my_custom_write
                    ),
                ),
                Characteristic(
                    "552957FB-CF1F-4A31-9535-E78847E1A714",
                    Characteristic.Properties.READ | Characteristic.Properties.WRITE,
                    Characteristic.READABLE | Characteristic.WRITEABLE,
                    CharacteristicValue(
                        read=self.my_custom_read_with_error,
                        write=self.my_custom_write_with_error,
                    ),
                ),
                Characteristic(
                    "486F64C6-4B5F-4B3B-8AFF-EDE134A8446A",
                    Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
                    Characteristic.READABLE,
                    bytes("hello", "utf-8"),
                ),
            ],
        )
        device.add_services([device_info_service, custom_service1])
        device.listener = Listener(device)

        return device

    def my_custom_read(self, connection):
        logging.info("----- READ from", connection)
        return bytes(f"Hello {connection}", "ascii")

    def my_custom_write(self, connection, value):
        logging.info(f"----- WRITE from {connection}: {value}")

    def my_custom_read_with_error(self, connection):
        logging.info("----- READ from", connection, "[returning error]")
        if connection.is_encrypted:
            return bytes([123])

        raise ATT_Error(ATT_INSUFFICIENT_ENCRYPTION_ERROR)

    def my_custom_write_with_error(self, connection, value):
        logging.info(f"----- WRITE from {connection}: {value}", "[returning error]")
        if not connection.is_encrypted:
            raise ATT_Error(ATT_INSUFFICIENT_ENCRYPTION_ERROR)
