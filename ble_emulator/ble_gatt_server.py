import asyncio
import dataclasses
import logging

from ble_device_1 import BleDevice1
from bumble.transport import open_transport_or_link
from bumble.transport.common import Transport


@dataclasses.dataclass
class BleGattServer:
    hci_transport: Transport
    device_1: BleDevice1


async def start_server_task() -> BleGattServer:
    """
    Start a GATT server in a separate task
    """
    gatt_server_future: asyncio.Future["BleGattServer"] = asyncio.Future()
    asyncio.create_task(_gatt_server_task(gatt_server_future))
    return await gatt_server_future


async def _gatt_server_task(gatt_server: asyncio.Future[BleGattServer]):
    try:
        logging.info("<<< connecting to HCI...")
        async with await open_transport_or_link("android-netsim") as hci_transport:
            logging.info("<<< connected")

            # Store the transport globally for use in the listener
            hci_transport = hci_transport

            # Create a device to manage the host
            device_1 = BleDevice1(hci_transport)

            # Get things going
            await device_1.power_on()

            # Connect to a peer
            await device_1.start_advertising(auto_restart=True)

            # Return the startet GATT Server
            gatt_server.set_result(BleGattServer(hci_transport, device_1))

            await hci_transport.source.wait_for_termination()  # type: ignore
    except Exception as e:
        logging.error(f"Error in GATT server task: {e}")
        gatt_server.set_exception(e)
