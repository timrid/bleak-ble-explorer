import contextlib
import dataclasses
from typing import AsyncIterator

from adb_helper import call_adb
from ble_peripheral import BlePeripheral1, BlePeripheralDatabase
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ble_peripherals = BlePeripheralDatabase()
    yield
    await app.state.ble_peripherals.stop_all()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/ping/")
async def ping():
    return "pong"


@app.post("/grant_permission/")
async def grant_permission(package: str, permission: str):
    call_adb(["shell", "pm", "grant", package, permission])


@app.post("/revoke_permission/")
async def revoke_permission(package: str, permission: str):
    call_adb(["shell", "pm", "revoke", package, permission])


@app.post("/activate_bluetooth/")
async def activate_bluetooth():
    btle_status = call_adb(["shell", "settings", "get", "global", "bluetooth_on"])
    print(f"{btle_status=}")
    if btle_status == "0":
        # Enable Bluetooth (A small hack with key events)
        call_adb(["shell", "am", "start", "-a", "android.settings.BLUETOOTH_SETTINGS"])
        call_adb(["shell", "input", "keyevent", "19"])  # Arrow up
        call_adb(["shell", "input", "keyevent", "23"])  # Enter


@app.post("/ble_peripheral/start/")
async def ble_peripheral_start(
    name: str = "Bumble", address: str = "F0:F1:F2:F3:F4:F5"
):
    peripheral = BlePeripheral1(name, address)
    await peripheral.start_peripheral()
    peripheral_id = app.state.ble_peripherals.add_peripheral(peripheral)
    return JSONResponse(
        status_code=200,
        content={"status": "GATT server task started", "peripheral_id": peripheral_id},
    )


@app.post("/ble_peripheral/stop/")
async def ble_peripheral_stop(peripheral_id: str):
    app.state.ble_peripherals.stop_peripheral(peripheral_id)
    return JSONResponse(
        status_code=200,
        content={"status": "Peripheral stopped"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")
