from adb_helper import call_adb
from ble_gatt_server import BleGattServer, start_server_task
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

global_ble_gatt_server: BleGattServer | None = None


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


@app.post("/gatt_server/start/")
async def gatt_server_start():
    global global_ble_gatt_server

    try:
        global_ble_gatt_server = await start_server_task()
        return JSONResponse(
            status_code=200,
            content={"status": "GATT server task started"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "GATT server failed",
                "error": str(e),
            },
        )


@app.post("/gatt_server/status/")
async def gatt_server_status():
    if global_ble_gatt_server is None:
        return JSONResponse(
            status_code=503,
            content={"status": "GATT server not running"},
        )
    else:
        return JSONResponse(
            status_code=200,
            content={"status": "GATT server running"},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
