import asyncio
import traceback
from typing import Callable

import toga
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from toga.style import Pack
from toga.style.pack import COLUMN, ROW  # type: ignore

from bleakbleexplorer.ble_device_box import BLEDeviceBox
from bleakbleexplorer.custom_list_view import CustomListRow, CustomListView


class BLEDeviceRow(CustomListRow):
    def __init__(
        self,
        device: BLEDevice,
        adv_data: AdvertisementData,
        on_connect: Callable[[BLEDevice, AdvertisementData], None],
    ):
        super().__init__()
        self.device = device
        self.adv_data = adv_data
        self.on_connect = on_connect
        self.details_shown = False

        self.divider_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        infos_box = toga.Box(style=Pack(direction=ROW, flex=1))

        name_box = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))
        name_box.add(
            toga.Label(
                device.name or "N/A",
                style=Pack(
                    font_weight="bold",
                    margin_left=5,
                ),
            )
        )
        name_box.add(
            toga.Label(
                f"{device.address}",
                style=Pack(
                    margin_left=5,
                ),
            )
        )
        infos_box.add(name_box)

        buttons_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
        buttons_box.add(
            toga.Label(
                f"{adv_data.rssi} dBm",
                style=Pack(
                    margin_left=1,
                ),
            ),
        )
        buttons_box.add(
            toga.Button(
                "Connect",
                on_press=self.on_connect_press,
                style=Pack(
                    margin_left=1,
                ),
            )
        )
        self.details_btn = toga.Button(
            "Show Details",
            on_press=self.on_details_press,
            style=Pack(
                margin_left=1,
            ),
        )
        buttons_box.add(self.details_btn)
        infos_box.add(buttons_box)
        self.divider_box.add(infos_box)

        self.add(self.divider_box)

    def on_connect_press(self, widget: toga.Widget):
        self.on_connect(self.device, self.adv_data)

    def on_details_press(self, widget: toga.Widget):
        if self.details_shown is False:
            self.show_details()
            self.details_shown = True
            self.details_btn.text = "Hide Details"
        else:
            self.divider_box.remove(self.divider)
            self.divider_box.remove(self.details_box)
            self.details_shown = False
            self.details_btn.text = "Show Details"

    def show_details(self):
        self.divider = toga.Divider()
        self.divider_box.add(self.divider)

        self.details_box = toga.Box(style=Pack(direction=ROW, flex=1))

        self.adv_data_txt = toga.MultilineTextInput(style=Pack(flex=1))
        self.divider_box.add(self.adv_data_txt)
        s = ""
        for company_id, data in self.adv_data.manufacturer_data.items():
            s += "Manufacturer Data:\n"
            s += f"Company: 0x{company_id:04X}\n"
            s += f"0x{data.hex().upper()}\n"
        for key, data in self.adv_data.service_data.items():
            s += f"Service Data ({key}):\n"
            s += f"0x{data.hex().upper()}\n"
        if self.adv_data.tx_power:
            s += f"TX-Power: {self.adv_data.tx_power}\n"
        for service_uuid in self.adv_data.service_uuids:
            s += f"Service UUID: {service_uuid}\n"
        self.adv_data_txt.value = s

        self.details_box.add(self.adv_data_txt)
        self.divider_box.add(self.details_box)


class ExceptionRow(CustomListRow):
    def __init__(self, ex: Exception):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5, flex=1))

        self.ex = ex
        label = toga.Label("Error:", style=Pack(font_weight="bold"))
        box.add(label)
        label = toga.MultilineTextInput(
            readonly=True,
            value=f"{ex}",
            style=Pack(flex=1),
        )
        box.add(label)

        self.add(box)


class InfoRow(CustomListRow):
    def __init__(self, info: str):
        super().__init__()
        box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        self.info = info
        label = toga.Label(f"{info}", style=Pack(font_weight="bold"))
        box.add(label)

        self.add(box)


class BLEScanResultsListView(CustomListView):
    def append_device(
        self,
        device: BLEDevice,
        adv_data: AdvertisementData,
        on_connect: Callable[[BLEDevice, AdvertisementData], None],
    ):
        self.add_row(BLEDeviceRow(device, adv_data, on_connect))

    def append_exception(self, ex: Exception):
        self.add_row(ExceptionRow(ex))

    def append_info(self, info: str):
        self.add_row(InfoRow(info))


class BLEScanBox(toga.Box):
    def __init__(
        self,
        main_window: toga.Window,
    ):
        super().__init__(style=Pack(direction=COLUMN))
        self.main_window = main_window

        self.scan_button = toga.Button(
            "Scan for BLE devices",
            on_press=self.start_scan,
        )
        self.scan_results_view = BLEScanResultsListView(
            style=Pack(direction=COLUMN, flex=1),
            horizontal=False,
        )

        self.scan_running = False

        self.add(self.scan_button)
        self.add(self.scan_results_view)

    async def start_scan(self, widget: toga.Widget):
        """Use scanner with 'with' container.

        The scan result in scanner.discovered_devices and
        scanner.discovered_devices_and_advertisement_data
        contains each discovered device only once.
        """
        if self.scan_running is True:
            return

        self.scan_button.enabled = False
        orig_btn_text = self.scan_button.text
        self.scan_button.text = "Scanning..."
        self.scan_results_view.clear()
        # self.scan_results_view.append_info("Scanning...")
        try:
            async with BleakScanner() as scanner:
                await asyncio.sleep(2)
                self.show_scan_results(
                    scanner.discovered_devices_and_advertisement_data
                )

        except Exception as e:
            traceback.print_exc()
            self.scan_results_view.append_exception(e)
        finally:
            self.scan_button.enabled = True
            self.scan_button.text = orig_btn_text

    def show_scan_results(self, data: dict[str, tuple[BLEDevice, AdvertisementData]]):
        """Show names of found devices and attached advertisment data.

        'data' is a dictionary, where the keys are the BLE addresses
        and the values are tuples of BLE device, advertisement data.
        """
        self.scan_results_view.clear()
        values = list(data.values())
        values = sorted(values, key=lambda value: value[1].rssi, reverse=True)
        for value in values:
            device, adv_data = value
            self.scan_results_view.append_device(
                device, adv_data, self.show_device_data
            )

    def show_device_data(self, device: BLEDevice, adv_data: AdvertisementData):
        self.main_window.content = BLEDeviceBox(self.main_window, self, device)
