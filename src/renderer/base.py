# Copyright (c) Paillat-dev
# SPDX-License-Identifier: MIT

import asyncio
import logging
import time
import urllib.parse
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import moviepy
import numpy as np
import playwright.async_api
from aiofiles import tempfile

from .manager import RendererManager

if TYPE_CHECKING:
    from .flag import Flag

logger = logging.getLogger("bot").getChild("flag_renderer")

GIF_HEIGHT: int = 256

# autocrop
GREENSCREEN_COLOR: tuple[int, int, int] = (26, 26, 30)
EDGE_IGNORE_PERCENT: float = 0.25
BOUND_MARGIN_PERCENT: float = 0.35  # Margin for sides and top
BOUND_MARGIN_BOTTOM_PERCENT: float = 0.5  # Extra margin for bottom (flagpole)
AUTO_CROP_THRESHOLD = 0.02

CLICK_TIMEOUT: float = 4 * 1000

LOAD_TIME_BONUS: float = +0.6

FILE_BUTTON_XPATH: str = (
    "xpath=/html/body/div[1]/div[1]/main/section/div[1]/div/div/fieldset/div/div[1]/fieldset/div/div[2]/label"
)
INPUT_FILE_BTN_XPATH: str = "xpath=/html/body/div[1]/div[1]/main/section/div[1]/div/div/fieldset/div/div[2]/div/div"
RESET_CAMERA_TEXT: str = "Reset camera"
THEATER_MODE_TEXT: str = "Theater mode"
SITE_PANEL_BTN_XPATH: str = "xpath=/html/body/div[1]/div[1]/header/div/div[2]/button"
WIND_CONTROL_TEXT: str = "Wind control"


class FlagRenderer:
    """Base class for renderers that provides common rendering methods."""

    def __init__(self, renderer_manager: RendererManager, flagwaver_url: str) -> None:
        self.renderer_manager: RendererManager = renderer_manager
        self.flagwaver_url: str = flagwaver_url

    @staticmethod
    def _is_greenscreen(pixel: np.ndarray, tolerance: int = 60) -> bool:
        """Check if a pixel is close to the greenscreen color."""
        return (
            abs(int(pixel[0]) - GREENSCREEN_COLOR[0]) < tolerance
            and abs(int(pixel[1]) - GREENSCREEN_COLOR[1]) < tolerance
            and abs(int(pixel[2]) - GREENSCREEN_COLOR[2]) < tolerance
        )

    async def _render_url_to_video(
        self,
        url_params: dict[str, str],
        temp_dir: str,
        viewport: dict[str, int] | None = None,
        device_scale_factor: int = 1,
        wait_until: str = "networkidle",
        wait_for: float = 1.0,
        wait_for_selector: str | None = None,
        duration: float = 6.0,
        exec_page: Callable[[playwright.async_api.Page], Coroutine[None, None, None]] | None = None,
    ) -> Path:
        """Render the HTML content to a gif and return the gif path.

        Args:
            url_params: The URL parameters to pass to Flagwaver.
            temp_dir: The temporary directory to store the video.
            viewport: The viewport size for the page.
            device_scale_factor: The device scale factor for high DPI rendering.
            wait_until: The event to wait for before rendering.
            wait_for: Additional time to wait for JS execution.
            wait_for_selector: The CSS selector to wait for before rendering.$
            duration: The duration of the video to capture.
            exec_page: A coroutine to execute on the page before rendering.

        Returns:
            The path to the rendered gif.

        """
        if not self.renderer_manager.browser:
            raise RuntimeError("Browser has not been initialized. Call 'start()' on RendererManager first.")

        context = await self.renderer_manager.browser.new_context(
            viewport=viewport,  # ty:ignore[invalid-argument-type]
            device_scale_factor=device_scale_factor,
            record_video_dir=temp_dir,
            record_video_size=viewport,  # ty:ignore[invalid-argument-type]
        )
        start_time = time.time()
        try:
            page = await context.new_page()
            try:
                encoded_url_params = urllib.parse.urlencode(url_params)
                await page.goto(f"{self.flagwaver_url}?{encoded_url_params}", wait_until=wait_until)  # ty:ignore[invalid-argument-type]
                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)

                await page.wait_for_timeout(wait_for)
                if exec_page:
                    await exec_page(page)
                load_time = (time.time() - start_time) + LOAD_TIME_BONUS
                logger.debug(f"Page loaded in {load_time:.2f} seconds")
                await asyncio.sleep(duration + LOAD_TIME_BONUS)
            finally:
                await page.close()
        finally:
            await context.close()
        video_path = await page.video.path()  # ty:ignore[possibly-missing-attribute]
        return await asyncio.to_thread(self._manipulate_video, Path(video_path), trim_time=load_time)

    def _detect_flag_bounds(self, frame: np.ndarray, tolerance: int = 35) -> tuple[int, int, int, int]:
        """Detect the flag boundaries in a frame by scanning for non-greenscreen pixels.

        Args:
            frame: A numpy array representing the frame (H, W, C) in RGB format.
            tolerance: Color tolerance for greenscreen detection.

        Returns:
            A tuple (x_min, y_min, x_max, y_max) representing the detected bounds.
        """
        height, width = frame.shape[:2]

        # Sample background colors from corners for diagnostics
        corner_samples = [
            ("top-left", frame[10, 10]),
            ("top-right", frame[10, width - 10]),
            ("bottom-left", frame[height - 10, 10]),
            ("bottom-right", frame[height - 10, width - 10]),
            ("center-top", frame[10, width // 2]),
        ]
        logger.debug("Background color samples:")
        for label, pixel in corner_samples:
            logger.debug(f"  {label}: RGB{tuple(pixel)}")

        ignore_x = int(width * EDGE_IGNORE_PERCENT)
        ignore_y = int(height * EDGE_IGNORE_PERCENT)

        search_left = ignore_x
        search_right = width - ignore_x
        search_top = ignore_y
        search_bottom = height - ignore_y

        left_bound = search_left
        for x in range(search_left, search_right):
            column = frame[search_top:search_bottom, x]
            non_white_ratio = sum(1 for pixel in column if not self._is_greenscreen(pixel, tolerance)) / len(column)
            if non_white_ratio >= AUTO_CROP_THRESHOLD:
                left_bound = x
                break

        right_bound = search_right
        for x in range(search_right - 1, search_left, -1):
            column = frame[search_top:search_bottom, x]
            non_white_ratio = sum(1 for pixel in column if not self._is_greenscreen(pixel, tolerance)) / len(column)
            if non_white_ratio >= AUTO_CROP_THRESHOLD:
                right_bound = x
                break

        top_bound = search_top
        for y in range(search_top, search_bottom):
            row = frame[y, search_left:search_right]
            non_white_ratio = sum(1 for pixel in row if not self._is_greenscreen(pixel, tolerance)) / len(row)
            if non_white_ratio >= AUTO_CROP_THRESHOLD:
                top_bound = y
                break

        bottom_bound = search_bottom
        for y in range(search_bottom - 1, search_top, -1):
            row = frame[y, search_left:search_right]
            non_white_ratio = sum(1 for pixel in row if not self._is_greenscreen(pixel, tolerance)) / len(row)
            if non_white_ratio >= AUTO_CROP_THRESHOLD:
                bottom_bound = y
                break

        detected_width = right_bound - left_bound
        detected_height = bottom_bound - top_bound
        margin_x = int(detected_width * BOUND_MARGIN_PERCENT)
        margin_y_top = int(detected_height * BOUND_MARGIN_PERCENT)  # Regular margin for top
        margin_y_bottom = int(detected_height * BOUND_MARGIN_BOTTOM_PERCENT)  # Extra margin for bottom (flagpole)

        x_min = max(0, left_bound - margin_x)
        y_min = max(0, top_bound - margin_y_top)
        x_max = min(width, right_bound + margin_x)
        y_max = min(height, bottom_bound + margin_y_bottom)

        logger.debug(f"Margins: top={margin_y_top}, bottom={margin_y_bottom}, sides={margin_x}")

        logger.debug(f"Detected flag bounds: ({x_min}, {y_min}) to ({x_max}, {y_max})")
        logger.debug(f"Detected size: {x_max - x_min}x{y_max - y_min}")

        return x_min, y_min, x_max, y_max

    def _manipulate_video(self, path: Path, trim_time: float) -> Path:
        new_path = path.parent / f"{path.stem}_cropped.gif"

        clip = moviepy.VideoFileClip(path)
        if trim_time >= clip.duration:
            logger.warning(f"trim_time ({trim_time}s) exceeds clip duration ({clip.duration}s), using 0")
            trim_time = 0

        sample_time = min(trim_time + 0.5, clip.duration - 0.1)
        sample_frame = clip.get_frame(sample_time)  # Returns RGB numpy array

        x_min, y_min, x_max, y_max = self._detect_flag_bounds(sample_frame)

        crop_width = x_max - x_min
        crop_height = y_max - y_min

        x_center = (x_min + x_max) // 2
        y_center = (y_min + y_max) // 2

        logger.debug(f"Cropping to detected bounds: {crop_width}x{crop_height} at center ({x_center}, {y_center})")

        crop = moviepy.vfx.Crop(width=crop_width, height=crop_height, x_center=x_center, y_center=y_center)
        clip = clip.with_effects([crop])

        clip = clip[trim_time:]
        clip.write_gif(new_path)
        logger.debug(f"Cropped video with transparency to {new_path}")
        return new_path

    async def _setup_ui(self, page: playwright.async_api.Page) -> None:
        try:
            side_panel_btn = page.locator(SITE_PANEL_BTN_XPATH)
            await side_panel_btn.click(timeout=CLICK_TIMEOUT)

            wind_control_btn = page.get_by_text(WIND_CONTROL_TEXT)
            await wind_control_btn.click(timeout=CLICK_TIMEOUT)

            await side_panel_btn.click(timeout=CLICK_TIMEOUT)

            reset_camera_btn = page.get_by_text(RESET_CAMERA_TEXT)
            await reset_camera_btn.click(timeout=CLICK_TIMEOUT, force=True)

            theater_mode_btn = page.get_by_text(THEATER_MODE_TEXT)
            await theater_mode_btn.click(timeout=CLICK_TIMEOUT, force=True)
        except playwright.async_api.TimeoutError:
            logger.exception("Failed to setup the UI")
            logger.debug("Page content: %s", await page.content())

    @asynccontextmanager
    async def render(self, flag: "Flag") -> AsyncIterator[Path]:
        async with tempfile.TemporaryDirectory() as temp_dir:
            yield await self._render_url_to_video(
                flag.to_url_params(),
                temp_dir=temp_dir,
                exec_page=self._setup_ui,
                viewport={"width": 960, "height": 540},
            )
