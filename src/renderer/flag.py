# SPDX-License-Identifier: MIT
# Copyright: 2025-2026 Paillat-dev
from dataclasses import dataclass
from typing import Literal


@dataclass
class Flag:
    url: str
    flag_pole_type: Literal["gallery"] = "gallery"
    background: Literal["blue-sky", "custom"] = "custom"
    backgroundcolor: str = "1a1a1e"

    def to_url_params(self) -> dict[str, str]:
        return {
            "src": self.url,
            "flagpoletype": self.flag_pole_type,
            "background": self.background,
            "backgroundcolor": self.backgroundcolor,
        }
