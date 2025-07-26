import logging

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
from bumble.transport.common import Transport


class Listener(Device.Listener, Connection.Listener):
    def __init__(self, device: Device):
        self.device = device

    def on_connection(self, connection):
        logging.info(f"=== Connected to {connection}")
        connection.listener = self

    def on_disconnection(self, reason):
        logging.info(f"### Disconnected, reason={reason}")


class BleDevice1(Device):
    def __init__(self, transport: Transport):
        config = DeviceConfiguration.from_dict(
            {
                "name": "Bumble",
                "address": "F0:F1:F2:F3:F4:F5",
                "advertising_interval": 2000,
                "keystore": "JsonKeyStore",
                "irk": "865F81FF5A8B486EAAE29A27AD9F77DC",
            }
        )
        super().__init__(config=config, host=Host(transport.source, transport.sink))

        self.listener = Listener(self)

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
        self.add_services([device_info_service, custom_service1])

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
