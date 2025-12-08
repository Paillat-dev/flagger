# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

import asyncio
import contextlib
import logging
from asyncio import Future
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Self

from playwright.async_api import Browser, Playwright, async_playwright

TaskType = tuple[
    Callable[..., Awaitable[Any]],
    tuple[Any, ...],
    dict[str, Any],
    Future[Any],
]

logger = logging.getLogger("bot").getChild("renderer_manager")


class RendererManager:
    """Manages the browser and task queue for rendering tasks."""

    def __init__(self, num_workers: int = 2) -> None:
        self.num_workers: int = num_workers
        self.queue: asyncio.Queue[TaskType | None] = asyncio.Queue()
        self.browser: Browser | None = None
        self.playwright: Playwright | None = None
        self.worker_tasks: list[asyncio.Task[None]] = []
        logger.debug("RendererManager initialized")

    async def start(self) -> None:
        """Start the browser and the worker tasks."""
        logger.info("Starting the browser and worker tasks")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.worker_tasks = [
            asyncio.create_task(self._worker(), name=f"worker-{i + 1}") for i in range(self.num_workers)
        ]
        logger.info(f"{self.num_workers} worker tasks started")

    async def _worker(self) -> None:
        """Worker task that processes tasks from the queue."""
        worker_name = asyncio.current_task().get_name()  # ty:ignore[possibly-missing-attribute]
        logger.debug(f"{worker_name} started")
        while True:
            task = await self.queue.get()
            if task is None:
                logger.info(f"{worker_name} received stop signal")
                self.queue.task_done()
                break
            func, args, kwargs, future = task
            try:
                logger.debug("%s started task: %s", worker_name, getattr(func, "__name__", func))
                result = await func(*args, **kwargs)
                future.set_result(result)
                logger.debug(
                    "%s completed task: %s",
                    worker_name,
                    getattr(func, "__name__", func),
                )
            except Exception as e:
                logger.exception(
                    "%s encountered an error in task: %s",
                    worker_name,
                    getattr(func, "__name__", func),
                )
                future.set_exception(e)
            self.queue.task_done()

    async def render[**P, R](self, func: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs) -> R:
        """Add a rendering task to the queue and return the result."""
        logger.info("Adding a rendering task to the queue: %s", getattr(func, "__name__", func))
        future: Future[Any] = asyncio.get_running_loop().create_future()
        await self.queue.put((func, args, kwargs, future))
        return await future

    @asynccontextmanager
    async def render_context_manager[**P, R](
        self, func: Callable[P, AbstractAsyncContextManager[R]], *args: P.args, **kwargs: P.kwargs
    ) -> AsyncGenerator[R]:
        """Queue a task that creates and manages an async context manager.

        Usage:
            async with renderer.render_context_manager(browser.new_page) as page:
                await page.goto("https://example.com")
                # page is automatically closed on exit
        """
        logger.info("Adding a context manager task to the queue: %s", getattr(func, "__name__", func))

        # Helper to create and enter the context manager
        async def enter_context() -> tuple[AbstractAsyncContextManager[R], R]:
            ctx_manager = func(*args, **kwargs)  # No await - this returns the context manager
            result = await ctx_manager.__aenter__()
            return ctx_manager, result

        # Queue the enter operation
        future: Future[tuple[Any, R]] = asyncio.get_running_loop().create_future()
        await self.queue.put((enter_context, (), {}, future))
        ctx_manager, result = await future

        try:
            yield result
        finally:
            # Queue the exit operation
            async def exit_context() -> None:
                await ctx_manager.__aexit__(None, None, None)

            exit_future: Future[None] = asyncio.get_running_loop().create_future()
            await self.queue.put((exit_context, (), {}, exit_future))
            await exit_future
            logger.debug("Context manager exited for: %s", getattr(func, "__name__", func))

    async def close(self) -> None:
        """Close the browser and stop the worker tasks."""
        logger.info("Closing the browser and stopping the worker tasks")
        for _ in range(self.num_workers):
            await self.queue.put(None)
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks)
        if self.browser:
            with contextlib.suppress(Exception):
                await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed and all worker tasks stopped")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        await self.close()

    async def __aenter__(self) -> Self:
        await self.start()
        return self
