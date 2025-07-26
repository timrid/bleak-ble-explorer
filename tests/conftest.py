import asyncio
import contextlib
import inspect
from dataclasses import dataclass
from typing import Generator

import pytest
from toga_android.libs.events import AndroidEventLoop

from .emulator_controller_client import EmulatorControllerClient

loop = None


@contextlib.contextmanager
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    global loop
    loop = AndroidEventLoop()
    yield loop
    loop.run_forever_cooperatively()


# This is copied from the toga testbed (https://github.com/beeware/toga/blob/b7c1e927a249068892f2e2b1e17d6725eda894c3/testbed/tests/conftest.py#L133-L189)


# Controls the event loop used by pytest-asyncio.
@pytest.fixture(scope="session")
def event_loop_policy():
    yield ProxyEventLoopPolicy(ProxyEventLoop(loop))


# Loop policy that ensures proxy loop is always used.
class ProxyEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self, proxy_loop: "ProxyEventLoop"):
        super().__init__()
        self._proxy_loop = proxy_loop

    def new_event_loop(self):
        return self._proxy_loop


# Proxy which forwards all tasks to another event loop in a thread-safe manner.
# It implements only the methods used by pytest-asyncio.
@dataclass
class ProxyEventLoop(asyncio.AbstractEventLoop):
    loop: object
    closed: bool = False

    # Used by ensure_future.
    def create_task(self, coro):  # type: ignore
        return ProxyTask(coro)

    def run_until_complete(self, future):
        if inspect.iscoroutine(future):
            coro = future
        elif isinstance(future, ProxyTask):
            coro = future.coro
        else:
            raise TypeError(f"Future type {type(future)} is not currently supported")
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()  # type: ignore

    async def shutdown_asyncgens(self):
        # The proxy event loop doesn't need to shut anything down; the
        # underlying event loop will shut down its own async generators.
        pass

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True


@dataclass
class ProxyTask:
    coro: object

    # Used by ensure_future.
    _source_traceback = None

    def done(self):
        return False


@pytest.fixture(scope="session")
def emulator_controller() -> EmulatorControllerClient:
    emulator_controller = EmulatorControllerClient()
    emulator_controller.ping()
    return emulator_controller
