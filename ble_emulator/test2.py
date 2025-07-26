import asyncio
from sys import argv

from bumble.core import AdvertisingData
from bumble.device import Connection, Device, DeviceConfiguration
from bumble.hci import Address
from bumble.transport import open_transport_or_link
from bumble.transport.common import Transport


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
    uv run test.py Device1 F0:F0:F0:F0:F0:F0
    uv run test.py Device3 F0:F0:F0:F0:F0:F3 Device4 F0:F0:F0:F0:F0:F4
    """
    transport = await open_transport_or_link("android-netsim")

    device = create_device(argv[1], argv[2], transport)
    await device.power_on()
    await device.start_advertising(auto_restart=True)
    print(f"start device {argv[1]}")

    await transport.source.terminated


asyncio.run(main())
