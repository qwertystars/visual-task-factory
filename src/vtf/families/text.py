"""Fonts bundled with matplotlib, so text renders the same on every machine."""

from functools import lru_cache
from pathlib import Path

import matplotlib
from PIL import ImageFont

_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


@lru_cache(maxsize=None)
def font(size: int, mono: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSansMono" if mono else "DejaVuSans"
    if bold:
        name += "-Bold"
    return ImageFont.truetype(str(_DIR / f"{name}.ttf"), size)
