import os
import sys
import tempfile
from pathlib import Path
from threading import Thread

import pytest

from .conftest import event_loop


def run_tests():
    project_path = Path(__file__).parent.parent
    os.chdir(project_path)

    # Determine any args to pass to pytest. If there aren't any,
    # default to running the whole test suite.
    args = sys.argv[1:]
    if len(args) == 0:
        args = ["tests"]

    returncode = pytest.main(
        [
            # Turn up verbosity
            "-vv",
            # Disable color
            "--color=no",
            # Run all async tests and fixtures using pytest-asyncio.
            "--asyncio-mode=auto",
            "--override-ini",
            "asyncio_default_fixture_loop_scope=session",
            # Overwrite the cache directory to somewhere writable
            "-o",
            f"cache_dir={tempfile.gettempdir()}/.pytest_cache",
        ]
        + args,
    )

    print(f">>>>>>>>>> EXIT {returncode} <<<<<<<<<<")


def main():
    with event_loop() as loop:
        thread = Thread(target=run_tests)

        # Queue a background task to run that will start the main thread. We
        # do this, instead of just starting the thread directly, so that we can
        # make sure the App has been fully initialized, and the event loop is
        # running.
        loop.call_soon_threadsafe(thread.start)


if __name__ == "__main__":
    main()
