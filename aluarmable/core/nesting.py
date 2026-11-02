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


@dataclass
class Piece:
    """Unidad de acomodo: una lámina o un par de láminas pegadas por un lado (con separación)."""

    hull: np.ndarray  # contorno convexo que se acomoda
    members: list[tuple[str, np.ndarray, np.ndarray | None]]  # (etiqueta, contorno, «arriba»)
    area: float


def _single(s: Sheet) -> Piece:
    return Piece(s.poly, [(s.label, s.poly, s.up)], s.area)


def _glue(a: Sheet, ia: int, b: Sheet, ib: int) -> tuple[np.ndarray, np.ndarray | None] | None:
    """Contorno de `b` movido para quedar contra el lado `ia` de `a` (lado `ib` de `b`), a GAP."""
    pa, pb = a.poly, b.poly
    p, q = pa[ia], pa[(ia + 1) % len(pa)]
    r, t = pb[ib], pb[(ib + 1) % len(pb)]
    da, db = q - p, t - r
    la = np.linalg.norm(da)
    ang = math.atan2(-da[1], -da[0]) - math.atan2(db[1], db[0])  # r→t paralelo a q→p
    c, sn = math.cos(ang), math.sin(ang)
    rot = np.array([[c, -sn], [sn, c]])
    out = (pa[ia] + pa[(ia + 1) % len(pa)]) / 2  # punto medio del lado de a
    sgn = 1.0 if Polygon(pa).exterior.is_ccw else -1.0
    normal = sgn * np.array([da[1], -da[0]]) / la  # hacia afuera de a
    if Polygon(pb).exterior.is_ccw != Polygon(pa).exterior.is_ccw:
        return None
    mid_b = ((pb[ib] + pb[(ib + 1) % len(pb)]) / 2) @ rot.T
    shift = out + normal * GAP - mid_b
    up = None if b.up is None else rot @ b.up
    return (pb @ rot.T) + shift, up


def pair_sheets(sheets: list[Sheet], tol: float = 0.06, max_waste: float = 0.30) -> list[Piece]:
    """Aparea láminas por lados de largo parecido, formando piezas casi paralelogramos.
    Voraz: de mayor a menor área, cada lámina toma la pareja de menor desperdicio del casco."""
    order = sorted((s for s in sheets if len(s.poly) >= 3), key=lambda s: -s.area)
    sides = [
        [
            float(np.linalg.norm(s.poly[(k + 1) % len(s.poly)] - s.poly[k]))
            for k in range(len(s.poly))
        ]
        for s in order
    ]
    free = set(range(len(order)))
    pieces: list[Piece] = []
    for i, a in enumerate(order):
        if i not in free:
            continue
        free.discard(i)
        best = None
        for j in sorted(free):
            if order[j].area < 0.25 * a.area:
                continue
            for ia, la in enumerate(sides[i]):
                for ib, lb in enumerate(sides[j]):
                    if abs(la - lb) > tol * max(la, lb) or la < 25.0:
                        continue
                    g = _glue(a, ia, order[j], ib)
                    if g is None:
                        continue
                    pts = np.vstack([a.poly, g[0]])
                    hull = Polygon(pts).convex_hull
                    waste = hull.area / (a.area + order[j].area) - 1.0
                    rect = hull.minimum_rotated_rectangle
                    xs, ys = np.array(rect.exterior.coords)[:4].T
                    e1 = math.hypot(xs[1] - xs[0], ys[1] - ys[0])
                    e2 = math.hypot(xs[2] - xs[1], ys[2] - ys[1])
                    if max(e1, e2) > CAN[0] - 4 or min(e1, e2) > CAN[1] - 4:
                        continue
                    if waste < max_waste and (best is None or waste < best[0]):
                        best = (waste, j, g, hull)
        if best is None:
            pieces.append(_single(a))
            continue
        _, j, (pb, ub), hull = best
        free.discard(j)
        hc = np.array(hull.exterior.coords)[:-1]
        if Polygon(hc).exterior.is_ccw is False:
            hc = hc[::-1]
        pieces.append(
            Piece(hc, [(a.label, a.poly, a.up), (order[j].label, pb, ub)], a.area + order[j].area)
        )
    return pieces


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


def nest(sheets: list[Sheet], max_open: int = 6, extra: int = 2, pair: bool = False) -> list[Can]:
    pieces = pair_sheets(sheets) if pair else [_single(s) for s in sheets if len(s.poly) >= 3]
    order = sorted(pieces, key=lambda pc: -Polygon(pc.hull).area)
    cans: list[Can] = []
    open_cans: list[Can] = []
    for s in order:
        base = Polygon(s.hull)
        placed = False
        for can in [*open_cans, None]:
            if can is None:
                can = Can()
                cans.append(can)
                open_cans.append(can)
                if len(open_cans) > max_open:
                    open_cans.pop(0)
            best = None
            for ang in _angles(s.hull, extra):
                rot = affinity.rotate(base, -ang, origin=(0, 0))
                r = _best_fit(can, rot)
                if r and (best is None or r[0] < best[0]):
                    best = (r[0], r[1], r[2], ang, rot)
            if best is None:
                if not can.items and can is cans[-1]:
                    raise ValueError(
                        f"la lámina {s.members[0][0]} no entra en la lata de {CAN[0]} × {CAN[1]} mm"
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
            can.area += s.area
            c, sn = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
            for label, poly, up_v in s.members:
                mp = affinity.translate(affinity.rotate(Polygon(poly), -ang, origin=(0, 0)), dx, dy)
                up = (
                    None
                    if up_v is None
                    else np.array([c * up_v[0] - sn * up_v[1], sn * up_v[0] + c * up_v[1]])
                )
                can.items.append(Placed(label, np.array(mp.exterior.coords)[:-1], ang, up))
            placed = True
            break
        assert placed
    return cans


def utilization(cans: list[Can]) -> float:
    return sum(c.area for c in cans) / (len(cans) * CAN[0] * CAN[1]) if cans else 0.0
