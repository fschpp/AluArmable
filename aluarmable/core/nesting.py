"""Acomodo de láminas sobre latas de 210 × 140 mm (§6.8, R3).

Heurística propia sobre una grilla de 1 mm: cada lata es una matriz de ocupación; para cada
pieza se prueban varias orientaciones y se busca por correlación (FFT) la posición libre de
menor «altura». Las piezas se guardan engrosadas por la separación mínima (GAP) para poder
cortarlas a mano. Orden: de mayor a menor área; primer ajuste en las latas abiertas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.signal import fftconvolve
from shapely import affinity, contains_xy
from shapely.geometry import Polygon

from .sheets import Sheet

CAN = (210.0, 140.0)
GAP = 3.0
PIX = 0.72  # semidiagonal de un píxel de 1 mm: engrosado conservador de la máscara
W_PX, H_PX = int(CAN[0]), int(CAN[1])


@dataclass
class Placed:
    label: str
    poly: np.ndarray  # coordenadas sobre la lata (mm)
    angle: float
    up: np.ndarray | None


@dataclass
class Can:
    items: list[Placed] = field(default_factory=list)
    occ: np.ndarray = field(default_factory=lambda: np.zeros((H_PX, W_PX), np.float32))
    area: float = 0.0


def _mask(poly: Polygon, grow: float) -> tuple[np.ndarray, float, float]:
    minx, miny, maxx, maxy = poly.bounds
    fat = poly.buffer(grow, join_style=2, mitre_limit=3.0)
    w, h = math.ceil(maxx - minx + 2 * grow) + 1, math.ceil(maxy - miny + 2 * grow) + 1
    xs = np.arange(w) + 0.5 + minx - grow
    ys = np.arange(h) + 0.5 + miny - grow
    X, Y = np.meshgrid(xs, ys)
    return contains_xy(fat, X, Y).astype(np.float32), minx - grow, miny - grow


def _angles(poly2: np.ndarray, extra: int) -> list[float]:
    best, best_ang = None, 0.0
    for ang in range(0, 180, 2):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        q = poly2 @ np.array([[c, -s], [s, c]])
        a = np.ptp(q[:, 0]) * np.ptp(q[:, 1])
        if best is None or a < best:
            best, best_ang = a, float(ang)
    step = 90.0 / max(extra, 1)
    return [(best_ang + k * step) % 360 for k in range(4 * max(extra, 1))]


def _best_fit(can: Can, poly: Polygon):
    """(puntaje, x0, y0) de la mejor posición libre de `poly` en la lata, o None."""
    m, ox, oy = _mask(poly, PIX)
    h, w = m.shape
    if w > W_PX or h > H_PX:
        return None
    ov = fftconvolve(can.occ, m[::-1, ::-1], mode="valid")
    ok = ov < 0.5
    if not ok.any():
        return None
    ys, xs = np.nonzero(ok)
    score = (ys + h) * 3.0 + xs  # prefiere abajo y a la izquierda (borde superior más bajo)
    k = int(np.argmin(score))
    return float(score[k]), float(xs[k]) - ox, float(ys[k]) - oy


def nest(sheets: list[Sheet], max_open: int = 6, extra: int = 2) -> list[Can]:
    order = sorted((s for s in sheets if len(s.poly) >= 3), key=lambda s: -s.area)
    cans: list[Can] = []
    open_cans: list[Can] = []
    for s in order:
        base = Polygon(s.poly)
        placed = False
        for can in [*open_cans, None]:
            if can is None:
                can = Can()
                cans.append(can)
                open_cans.append(can)
                if len(open_cans) > max_open:
                    open_cans.pop(0)
            best = None
            for ang in _angles(s.poly, extra):
                rot = affinity.rotate(base, -ang, origin=(0, 0))
                r = _best_fit(can, rot)
                if r and (best is None or r[0] < best[0]):
                    best = (r[0], r[1], r[2], ang, rot)
            if best is None:
                if not can.items and can is cans[-1]:
                    raise ValueError(
                        f"la lámina {s.label} no entra en la lata de {CAN[0]} × {CAN[1]} mm"
                    )
                continue
            _, dx, dy, ang, rot = best
            pl = affinity.translate(rot, dx, dy)
            m, ox, oy = _mask(pl, PIX + GAP)
            x0, y0 = round(ox), round(oy)
            for yy in range(m.shape[0]):
                gy = y0 + yy
                if 0 <= gy < H_PX:
                    row = m[yy]
                    xa, xb = max(x0, 0), min(x0 + m.shape[1], W_PX)
                    if xb > xa:
                        can.occ[gy, xa:xb] = np.maximum(can.occ[gy, xa:xb], row[xa - x0 : xb - x0])
            can.area += pl.area
            up = None
            if s.up is not None:
                c, sn = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
                up = np.array([c * s.up[0] - sn * s.up[1], sn * s.up[0] + c * s.up[1]])
            can.items.append(Placed(s.label, np.array(pl.exterior.coords)[:-1], ang, up))
            placed = True
            break
        assert placed
    return cans


def utilization(cans: list[Can]) -> float:
    return sum(c.area for c in cans) / (len(cans) * CAN[0] * CAN[1]) if cans else 0.0
