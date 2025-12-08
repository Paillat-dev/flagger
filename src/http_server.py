# Copyright (c) NiceBots
# SPDX-License-Identifier: MIT

import asyncio
import contextlib
from pathlib import Path
from typing import Self


class HttpServer:
    def __init__(self, port: int, path: Path) -> None:
        self.port = port
        self.path = path
        self.process: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self.process = await asyncio.create_subprocess_shell(
            f"python -m http.server {self.port} --directory {self.path}"
        )

        await asyncio.sleep(1)  # Give the server a moment to start

    async def stop(self) -> None:
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: object
    ) -> None:
        with contextlib.suppress(ProcessLookupError):
            await self.stop()


__all__ = ["HttpServer"]
