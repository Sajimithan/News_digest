import asyncio
from typing import Callable, TypeVar


T = TypeVar("T")


def run_sync(func: Callable[..., T], *args, **kwargs) -> T:
    return func(*args, **kwargs)


async def to_thread(func: Callable[..., T], *args, **kwargs) -> T:
    return await asyncio.to_thread(run_sync, func, *args, **kwargs)
