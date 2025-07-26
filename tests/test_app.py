import asyncio

from bleak import BleakScanner

from .emulator_controller_client import EmulatorControllerClient


def test_first():
    """An initial test for the app."""
    assert 1 + 1 == 2


def test_first2(emulator_controller: EmulatorControllerClient):
    """An initial test for the app."""
    emulator_controller.ping()
    emulator_controller.grand_permission(
        package="com.timrid.bleakbleexplorer",
        permission="android.permission.BLUETOOTH_SCAN",
    )
    emulator_controller.activate_bluetooth()
    emulator_controller.gatt_server_start()


async def test_bleak_scanner(emulator_controller: EmulatorControllerClient):
    # breakpoint()
    async with BleakScanner() as scanner:
        await asyncio.sleep(5)
        assert len(scanner.discovered_devices) == 1


async def test_bleak_scanner2():
    result = await BleakScanner.discover(return_adv=True)
    assert len(result) == 1
