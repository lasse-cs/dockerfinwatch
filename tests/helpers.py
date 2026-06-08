import asyncio
from collections.abc import Callable


async def wait_until(predicate: Callable[[], bool], timeout_seconds: float = 1) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    assert predicate()
