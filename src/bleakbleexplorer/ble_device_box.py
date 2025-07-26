import asyncio

import toga
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from toga.style import Pack
from toga.style.pack import COLUMN, ROW  # type: ignore

from bleakbleexplorer.custom_list_view import CustomListRow, CustomListView


class ServiceRow(CustomListRow):
    def __init__(self, service: BleakGATTService):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        self.service = service
        label = toga.Label("Service:", style=Pack(font_weight="bold"))
        box.add(label)
        label = toga.Label(f"{service.uuid}")
        box.add(label)

        self.add(box)


class CharacteristicRow(CustomListRow):
    def __init__(self, client: BleakClient, characteristic: BleakGATTCharacteristic):
        super().__init__()
        self.client = client
        self.characteristic = characteristic

        box = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        label = toga.Label("Characteristic", style=Pack(font_weight="bold"))
        box.add(label)

        label = toga.Label(f"{characteristic.uuid}")
        box.add(label)
        label = toga.Label(f"{characteristic.description}")
        box.add(label)
        self.data_lbl = toga.Label("")
        box.add(self.data_lbl)

        button_box = toga.Box(style=Pack(direction=ROW, margin=5))
        for prop in characteristic.properties:
            if prop == "read":
                btn = toga.Button(text="Read", on_press=self.read)
            else:
                btn = toga.Button(text=prop, enabled=False)
            button_box.add(btn)
        box.add(button_box)

        self.add(box)

    async def read(self, widget: toga.Widget):
        data = await self.client.read_gatt_char(self.characteristic)
        self.data_lbl.text = str(data)


class DescriptorRow(CustomListRow):
    def __init__(self, descriptor: BleakGATTDescriptor):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        self.descriptor = descriptor
        label = toga.Label("Descriptor", style=Pack(font_weight="bold"))
        box.add(label)
        label = toga.Label(f"{descriptor.description}")
        box.add(label)
        label = toga.Label(f"{descriptor.uuid}")
        box.add(label)

        self.add(box)


class BLEServiceListView(CustomListView):
    def set_services(self, client: BleakClient, services: BleakGATTServiceCollection):
        self.clear()
        for service in services:
            self.add_row(ServiceRow(service))
            for characteristic in service.characteristics:
                self.add_row(CharacteristicRow(client, characteristic))
                for descriptor in characteristic.descriptors:
                    self.add_row(DescriptorRow(descriptor))


class BLEDeviceBox(toga.Box):
    def __init__(
        self,
        main_window: toga.Window,
        parent_box: toga.Box,
        device: BLEDevice,
    ):
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        self.main_window = main_window
        self.parent_box = parent_box
        self.device = device

        back_button = toga.Button("Back", on_press=self.show_main_box)

        title = toga.Label(
            device.name or f"No name ({device.address})",
            style=Pack(font_weight="bold", font_size=20, align_items="center"),
        )

        self.connecting_lbl = toga.Label("")

        self.services_view = BLEServiceListView(
            style=Pack(direction=COLUMN, flex=1),
            horizontal=False,
        )

        self.add(back_button)
        self.add(title)

        self.add(self.connecting_lbl)
        self.add(self.services_view)

        self.con_task = asyncio.create_task(self.connection_task(self.device))
        self.client: BleakClient | None = None

    async def connection_task(self, device: BLEDevice):
        self.connecting_lbl.text = "Connecting..."
        while True:
            try:
                async with BleakClient(device) as client:
                    self.client = client
                    self.connecting_lbl.text = "Connected"
                    self.services_view.set_services(client, client.services)
                    while True:
                        await asyncio.sleep(0.2)
                        if client.is_connected is False:
                            break
                self.connecting_lbl.text = "Disconnected. Try reconnecting..."
                self.services_view.clear()
            except Exception as e:
                self.connecting_lbl.text = f"ERROR: {e}"

    def show_main_box(self, widget: toga.Widget):
        self.con_task.cancel()
        self.main_window.content = self.parent_box
        self.main_window.content = self.parent_box
