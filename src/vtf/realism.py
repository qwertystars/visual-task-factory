"""Seeded photo-realism helpers shared by the document and clock renderers.

Everything here is a pure function of its inputs and an explicit numpy Generator, so the
same knobs give the same bytes. Array maths sticks to + - * / and sqrt (no exp/sin on
large arrays) and leaves resampling to Pillow, to keep results stable across machines.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def value_noise(rng: np.random.Generator, h: int, w: int, cells: int) -> np.ndarray:
    """Smooth noise in [0, 1]: a small random grid upsampled with bicubic resampling."""
    gh, gw = max(2, h * cells // max(h, w)), max(2, w * cells // max(h, w))
    grid = (rng.random((gh + 1, gw + 1)) * 255).astype(np.uint8)
    up = Image.fromarray(grid, "L").resize((w, h), Image.BICUBIC)
    return np.asarray(up, dtype=np.float32) / 255.0


def paper(rng, w: int, h: int, base=(250, 248, 242), blotch: float = 6.0, grain: float = 4.0,
          fibers: int = 0) -> np.ndarray:
    """Paper texture as an (h, w, 3) uint8 array: blotchy tone, fine grain, a few fibres."""
    arr = np.empty((h, w, 3), np.float32)
    arr[:] = base
    low = value_noise(rng, h, w, 6) - 0.5
    mid = value_noise(rng, h, w, 40) - 0.5
    arr += (blotch * low + 0.5 * blotch * mid)[..., None]
    arr += (rng.random((h, w, 1), dtype=np.float32) - 0.5) * grain
    if fibers:
        img = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        for _ in range(fibers):
            x, y = rng.random() * w, rng.random() * h
            dx, dy = (rng.random() - 0.5) * 30, (rng.random() - 0.5) * 30
            d.line([(x, y), (x + dx, y + dy)], fill=(150, 140, 120, int(rng.integers(14, 34))), width=1)
        return np.asarray(img).copy()
    return np.clip(arr + 0.5, 0, 255).astype(np.uint8)


def surface(rng, w: int, h: int, kind: str) -> np.ndarray:
    """A desk or table top behind a document."""
    base = {"wood": (122, 86, 58), "desk": (78, 82, 88), "linen": (196, 190, 178), "slate": (52, 56, 60)}[kind]
    arr = np.empty((h, w, 3), np.float32)
    arr[:] = base
    if kind == "wood":
        # stretched noise gives grain along x
        grain = np.asarray(Image.fromarray((rng.random((max(2, h // 6), 4)) * 255).astype(np.uint8), "L")
                           .resize((w, h), Image.BICUBIC), np.float32) / 255.0 - 0.5
        arr += (grain * 36)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)
    arr += ((value_noise(rng, h, w, 8) - 0.5) * 18)[..., None]
    arr += (rng.random((h, w, 1), dtype=np.float32) - 0.5) * 8
    return np.clip(arr + 0.5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- geometry

def homography(src, dst) -> np.ndarray:
    """3x3 matrix mapping the 4 src points onto the 4 dst points."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A, float), np.array(b, float))
    return np.round(np.append(h, 1.0).reshape(3, 3), 10)


def apply_h(H, pts) -> list[tuple[float, float]]:
    out = []
    for x, y in pts:
        u, v, w = H @ np.array([x, y, 1.0])
        out.append((float(u / w), float(v / w)))
    return out


def quad(w: float, h: float, cx: float, cy: float, rot_deg: float, persp: float, rng) -> list[tuple[float, float]]:
    """Where the corners of a w x h sheet land: rotated about (cx, cy), corners nudged by persp * size."""
    r = np.deg2rad(rot_deg)
    c, s = float(np.cos(r)), float(np.sin(r))
    out = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        jx, jy = (rng.random() - 0.5) * 2 * persp * w, (rng.random() - 0.5) * 2 * persp * h
        x, y = x + jx, y + jy
        out.append((cx + c * x - s * y, cy + s * x + c * y))
    return out


def warp(img: Image.Image, H: np.ndarray, size: tuple[int, int], resample=Image.BICUBIC) -> Image.Image:
    """Warp img by H (source -> output pixels) onto a canvas of the given size."""
    inv = np.linalg.inv(H)
    inv = inv / inv[2, 2]
    coeffs = [round(float(v), 12) for v in inv.flatten()[:8]]
    return img.transform(size, Image.PERSPECTIVE, coeffs, resample=resample)


def place(sheet_rgb: np.ndarray, sheet_alpha: np.ndarray, bg: np.ndarray, H: np.ndarray,
          shadow=(8, 10), shadow_blur: float = 7.0, shadow_strength: float = 0.45) -> np.ndarray:
    """Composite a warped sheet with a soft drop shadow onto bg."""
    h, w = bg.shape[:2]
    rgb = warp(Image.fromarray(sheet_rgb), H, (w, h))
    a = warp(Image.fromarray(sheet_alpha, "L"), H, (w, h))
    sh = Image.new("L", (w, h), 0)
    sh.paste(a, shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(shadow_blur))
    out = bg.astype(np.float32) * (1 - shadow_strength * np.asarray(sh, np.float32)[..., None] / 255.0)
    af = np.asarray(a, np.float32)[..., None] / 255.0
    out = out * (1 - af) + np.asarray(rgb, np.float32) * af
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- light and ink

def lighting(arr: np.ndarray, gx: float, gy: float, strength: float, vignette: float, warm: float = 0.0) -> np.ndarray:
    """Uneven light: a linear falloff along (gx, gy), darker corners, a slight colour cast."""
    h, w = arr.shape[:2]
    y = (np.arange(h, dtype=np.float32)[:, None] / max(1, h - 1)) * 2 - 1
    x = (np.arange(w, dtype=np.float32)[None, :] / max(1, w - 1)) * 2 - 1
    lin = 1 - strength * (0.5 + 0.5 * (gx * x + gy * y) / max(1e-6, abs(gx) + abs(gy)))
    vig = 1 - vignette * (x * x + y * y) / 2
    gain = (lin * vig)[..., None] * np.array([1 + warm, 1.0, 1 - warm], np.float32)
    return np.clip(arr.astype(np.float32) * gain + 0.5, 0, 255).astype(np.uint8)


def thermal(mask: np.ndarray, rng, fade: float, dropout: float) -> np.ndarray:
    """Thermal print wear on an ink mask in [0, 1]: faint vertical head streaks and dot dropout."""
    h, w = mask.shape
    streak = np.asarray(Image.fromarray((rng.random((2, max(2, w // 3))) * 255).astype(np.uint8), "L")
                        .resize((w, h), Image.BICUBIC), np.float32) / 255.0
    col = 1 - fade * streak[0:1, :] * streak[0:1, :]
    keep = (rng.random((h, w), dtype=np.float32) >= dropout).astype(np.float32)
    return mask * col * keep


def ink(paper_rgb: np.ndarray, mask: np.ndarray, color, strength: float = 1.0) -> np.ndarray:
    m = (mask * strength)[..., None]
    out = paper_rgb.astype(np.float32) * (1 - m) + np.array(color, np.float32) * m
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def sensor(arr: np.ndarray, rng, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return arr
    n = rng.standard_normal(arr.shape[:2], dtype=np.float32)[..., None] * sigma
    return np.clip(arr.astype(np.float32) + n + 0.5, 0, 255).astype(np.uint8)


def blur(arr: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return arr
    return np.asarray(Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius)))


def polygon_mask(shape, poly) -> np.ndarray:
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
    return np.asarray(m).astype(bool)


# ---------------------------------------------------------------- barcode

_L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
_G = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001", "0001001", "0010111"]
_R = ["1110010", "1100110", "1101100", "1000010", "1011100", "1001110", "1010000", "1000100", "1001000", "1110100"]
_PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def ean13(digits12: str) -> tuple[str, str]:
    """Full 13-digit code (with check digit) and its 95-module bar pattern."""
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits12))
    code = digits12 + str((10 - s % 10) % 10)
    par = _PARITY[int(code[0])]
    bits = "101"
    for i, d in enumerate(code[1:7]):
        bits += (_L if par[i] == "L" else _G)[int(d)]
    bits += "01010"
    for d in code[7:]:
        bits += _R[int(d)]
    return code, bits + "101"
