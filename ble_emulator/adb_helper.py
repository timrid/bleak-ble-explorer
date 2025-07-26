import os
import subprocess
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    adb_executable = "adb.exe"
else:
    adb_executable = "adb"

ADB_PATH = Path(os.environ["ANDROID_HOME"]) / "platform-tools" / adb_executable

if not ADB_PATH.exists():
    raise FileNotFoundError(
        f"ADB executable not found at {ADB_PATH}. Please set the ANDROID_HOME environment variable correctly."
    )


def call_adb(command: list[str]) -> str:
    try:
        result = subprocess.run(
            [ADB_PATH] + command,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error_output = exc.stderr or exc.stdout or str(exc)
        raise Exception(f"ADB command failed: {error_output}") from exc
