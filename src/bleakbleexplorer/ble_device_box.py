import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak_example.custom_list_view import CustomListRow, CustomListView


class ServiceRow(CustomListRow):
    def __init__(self, service: BleakGATTService):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        self.service = service
        label = toga.Label("Service:", style=Pack(font_weight="bold"))
        box.add(label)
        label = toga.Label(f"{service.uuid}")
        box.add(label)

        self.add(box)


class CharacteristicRow(CustomListRow):
    def __init__(self, characteristic: BleakGATTCharacteristic):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        self.characteristic = characteristic
        label = toga.Label("Characteristic", style=Pack(font_weight="bold"))
        box.add(label)

        label = toga.Label(f"{characteristic.uuid}")
        box.add(label)

        button_box = toga.Box(style=Pack(direction=ROW, margin=5))
        for prop in characteristic.properties:
            btn = toga.Button(text=prop)
            button_box.add(btn)
        box.add(button_box)

        self.add(box)


class DescriptorRow(CustomListRow):
    def __init__(self, descriptor: BleakGATTDescriptor):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        self.descriptor = descriptor
        label = toga.Label("Descriptor", style=Pack(font_weight="bold"))
        box.add(label)
        label = toga.Label(f"{descriptor.uuid}")
        box.add(label)

        self.add(box)


class BLEServiceListView(CustomListView):
    def set_services(self, services: BleakGATTServiceCollection):
        self.clear()
        for service in services:
            self.add_row(ServiceRow(service))
            for characteristic in service.characteristics:
                self.add_row(CharacteristicRow(characteristic))
                for descriptor in characteristic.descriptors:
                    self.add_row(DescriptorRow(descriptor))


class BLEDeviceBox(toga.Box):
    def __init__(
        self,
        main_window: toga.Window,
        parent_box: toga.Box,
        device: BLEDevice,
        adv_data: AdvertisementData,
    ):
        super().__init__(style=Pack(direction=COLUMN, flex=1))
        self.main_window = main_window
        self.parent_box = parent_box
        self.device = device
        self.adv_data = adv_data

        back_button = toga.Button("Back", on_press=self.show_main_box)

        title = toga.Label(
            device.name or f"No name ({device.address})",
            style=Pack(font_weight="bold", font_size=20, align_items="center"),
        )

        self.adv_data_txt = toga.MultilineTextInput()

        connect_button = toga.Button("Connect", on_press=self.connect_client)

        self.services_view = BLEServiceListView(
            style=Pack(direction=COLUMN, flex=1),
            horizontal=False,
        )

        self.add(back_button)
        self.add(title)
        self.add(self.adv_data_txt)
        self.add(connect_button)
        self.add(self.services_view)

        self.show_adv_data()

    def show_adv_data(self):
        s = ""
        for company_id, data in self.adv_data.manufacturer_data.items():
            s += f"Manufacturer Data ({company_id}): {data.hex(' ')}\n"
        for key, data in self.adv_data.service_data.items():
            s += f"Service Data ({key}): {data.hex(' ')}\n"
        s += f"RSSI: {self.adv_data.rssi}\n"
        if self.adv_data.tx_power:
            s += f"TX-Power: {self.adv_data.tx_power}\n"
        for service_uuid in self.adv_data.service_uuids:
            s += f"Service UUID: {service_uuid}\n"
        self.adv_data_txt.value = s

    async def connect_client(self, widget):
        async with BleakClient(self.device) as client:
            self.services_view.set_services(client.services)

    def show_main_box(self, widget):
        self.main_window.content = self.parent_box
