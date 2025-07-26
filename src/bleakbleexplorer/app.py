"""
Example Applikation for the BLE Library "bleak"
"""

import toga
from bleakbleexplorer.ble_scan_box import BLEScanBox

toga.Widget.DEBUG_LAYOUT_ENABLED = True


class BleakBLEExplorer(toga.App):
    """Construct and show the Toga application.

    Usually, you would add your application to a main content box.
    We then create a main window (with a name matching the app), and
    show the main window.
    """

    def startup(self):
        """Set up the GUI."""
        main_window = toga.MainWindow(title="BLE Scanner Demo App")

        main_box = BLEScanBox(main_window)

        main_window.content = main_box

        self.main_window = main_window
        main_window.show()


def main():
    return BleakBLEExplorer()
