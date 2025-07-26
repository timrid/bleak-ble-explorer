import asyncio
import logging
from sys import argv

from bumble.core import AdvertisingData
from bumble.device import Connection, Device, DeviceConfiguration
from bumble.hci import Address
from bumble.transport import open_transport_or_link
from bumble.transport.common import Transport

# Logging-Konfiguration
logging.basicConfig(
    level=logging.DEBUG,  # zeigt alle Logs ab DEBUG-Level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Listener(Device.Listener, Connection.Listener):
    def __init__(self, device):
        self.device = device

    def on_connection(self, connection):
        print(f"=== Connected to {connection}")
        connection.listener = self

    def on_disconnection(self, reason):
        print(f"### Disconnected, reason={reason}")


def create_device(name: str, address: str, transport: Transport) -> Device:
    config = DeviceConfiguration(
        name=name,
        address=Address(address),
        advertising_data=bytes(
            AdvertisingData(
                [(AdvertisingData.COMPLETE_LOCAL_NAME, bytes(name, "utf-8"))]
            )
        ),
    )
    device = Device.from_config_with_hci(config, transport.source, transport.sink)
    device.listener = Listener(device)

    return device


async def main():
    """
    uv run test.py Device1 F0:F0:F0:F0:F0:F0 Device2 F0:F0:F0:F0:F0:F1
    uv run test.py Device3 F0:F0:F0:F0:F0:F3 Device4 F0:F0:F0:F0:F0:F4
    """
    transports = []

    for name, address in zip(argv[1::2], argv[2::2]):
        print(name)
        print(address)
        print("open transport")
        transport = await open_transport_or_link("android-netsim")
        transports.append(transport)

        print("Create device")
        device = create_device(name, address, transport)

        print("Power on")
        await device.power_on()

        print("start_advertising")
        await device.start_advertising(auto_restart=True)
        print(f"start device {argv[1]}")

    await asyncio.gather(*[e.source.terminated for e in transports])


asyncio.run(main())
