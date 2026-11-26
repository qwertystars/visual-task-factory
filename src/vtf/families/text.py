"""Fonts that ship with the package, so text renders the same on every machine.

DejaVu comes with matplotlib. PT Sans, PT Sans Narrow, PT Serif and Courier Prime are
vendored under vtf/fonts with their OFL licence files.
"""

from functools import lru_cache
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from PIL import ImageFont

_DEJAVU = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
_VENDOR = Path(__file__).resolve().parent.parent / "fonts"

FILES = {
    ("sans", False): _VENDOR / "ptsans" / "PT_Sans-Web-Regular.ttf",
    ("sans", True): _VENDOR / "ptsans" / "PT_Sans-Web-Bold.ttf",
    ("narrow", False): _VENDOR / "ptsansnarrow" / "PT_Sans-Narrow-Web-Regular.ttf",
    ("narrow", True): _VENDOR / "ptsansnarrow" / "PT_Sans-Narrow-Web-Bold.ttf",
    ("serif", False): _VENDOR / "ptserif" / "PT_Serif-Web-Regular.ttf",
    ("serif", True): _VENDOR / "ptserif" / "PT_Serif-Web-Bold.ttf",
    ("courier", False): _VENDOR / "courierprime" / "CourierPrime-Regular.ttf",
    ("courier", True): _VENDOR / "courierprime" / "CourierPrime-Bold.ttf",
    ("dejavu", False): _DEJAVU / "DejaVuSans.ttf",
    ("dejavu", True): _DEJAVU / "DejaVuSans-Bold.ttf",
    ("mono", False): _DEJAVU / "DejaVuSansMono.ttf",
    ("mono", True): _DEJAVU / "DejaVuSansMono-Bold.ttf",
}


@lru_cache(maxsize=None)
def font(size: int, mono: bool = False, bold: bool = False, face: str | None = None) -> ImageFont.FreeTypeFont:
    face = face or ("mono" if mono else "dejavu")
    return ImageFont.truetype(str(FILES[(face, bold)]), size)


@lru_cache(maxsize=None)
def register_mpl_fonts() -> dict[str, str]:
    """Add the vendored fonts to matplotlib; returns face -> matplotlib family name."""
    names = {}
    for (face, _), p in FILES.items():
        font_manager.fontManager.addfont(str(p))
        names[face] = font_manager.FontProperties(fname=str(p)).get_name()
    return names
