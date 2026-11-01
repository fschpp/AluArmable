"""Polígono de cada lámina de lata: cara retranqueada, esquinas cortadas por la raíz del nudo
y puntas agudas recortadas (§5.4, §6.3, R3)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon
from shapely.geometry import box as sbox
from shapely.ops import unary_union

from .params import Profile
from .pbn import PBN, Panel, to_2d

TIP_WIDTH = 8.0  # ancho al que se recorta una punta aguda (mm)
TIP_ANGLE = 25.0  # ángulo bajo el cual se recorta la punta (°)
R_MIN = 7.0  # radio de raíz mínimo del nudo (mm)
ROOT_MARGIN = 1.5


@dataclass
class Sheet:
    label: str
    poly: np.ndarray  # (n, 2) contorno antihorario visto desde afuera, mm
    face: np.ndarray  # contorno de la cara (sin retranqueo), mismo sistema
    up: np.ndarray | None  # dirección «arriba» (+Z) en el plano de la lámina, o None
    area: float
    trimmed: int  # cantidad de puntas recortadas
    panel: int


def root_radius(g: PBN, node: int, bar: int, w: float) -> float:
    """Radio de raíz de la barra `bar` en el nudo `node`: R = max(Rmín, W/tan(θ/2) + 1,5), con θ
    el menor ángulo entre esa barra y las otras barras del nudo (§5.3)."""
    nd = g.nodes[node]

    def direction(bid: int) -> np.ndarray:
        b = g.bars[bid]
        o = g.nodes[b.b if b.a == node else b.a].pos - nd.pos
        return o / np.linalg.norm(o)

    d0 = direction(bar)
    th = 180.0
    for other in nd.bars:
        if other != bar:
            th = min(th, math.degrees(math.acos(float(np.clip(d0 @ direction(other), -1, 1)))))
    th = max(th, 5.0)
    return max(R_MIN, w / math.tan(math.radians(th) / 2) + ROOT_MARGIN)


def _bars_at(g: PBN, panel: Panel, node: int) -> list[int]:
    return [b.id for b in (g.bars[i] for i in g.nodes[node].bars) if panel.id in (b.p1, b.p2)]


def make_sheet(g: PBN, panel: Panel, prof: Profile) -> Sheet:
    pts3 = np.array([g.nodes[i].pos for i in panel.nodes])
    p2 = to_2d(pts3)
    face = Polygon(p2)
    shape = face.buffer(-prof.e, join_style=2, mitre_limit=10.0)
    trimmed = 0
    corners = panel.corners
    idx = {n: k for k, n in enumerate(panel.nodes)}
    for n in corners:
        k = idx[n]
        v = p2[k]
        a = p2[(k - 1) % len(p2)] - v
        b = p2[(k + 1) % len(p2)] - v
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        if la < 1e-9 or lb < 1e-9:
            continue
        a, b = a / la, b / lb
        alpha = math.degrees(math.acos(float(np.clip(a @ b, -1, 1))))
        if alpha >= 179.0:
            continue
        r = max((root_radius(g, n, bid, prof.W) for bid in _bars_at(g, panel, n)), default=R_MIN)
        cut = r
        if alpha < TIP_ANGLE:
            d8 = TIP_WIDTH / (2 * math.tan(math.radians(alpha) / 2))
            cut = max(cut, d8)
            trimmed += 1
        bis = (a + b) / np.linalg.norm(a + b)
        # semiplano {x: (x − v)·bis ≥ cut}: se queda con lo que está lejos del vértice
        t = np.array([-bis[1], bis[0]])
        big = 1e4
        c0 = v + bis * cut
        half = Polygon(
            [c0 + t * big, c0 - t * big, c0 - t * big + bis * big, c0 + t * big + bis * big]
        )
        shape = shape.intersection(half)
        if shape.is_empty:
            break
    if shape.is_empty:
        poly = np.zeros((0, 2))
        area = 0.0
    else:
        if shape.geom_type != "Polygon":  # varias partes: queda la mayor
            shape = max(shape.geoms, key=lambda s: s.area)
        poly = np.array(shape.exterior.coords)[:-1]
        area = float(shape.area)
    # «arriba» (+Z) en el sistema 2D de la lámina
    from .pbn import _frame

    _, u, v = _frame(pts3)
    up = np.array([u[2], v[2]])
    up = None if np.linalg.norm(up) < 0.2 else up / np.linalg.norm(up)
    return Sheet(panel.label, poly, p2, up, area, trimmed, panel.id)


def make_sheets(g: PBN, prof: Profile | None = None) -> list[Sheet]:
    prof = prof or Profile()
    return [make_sheet(g, p, prof) for p in g.panels]


def union_area(polys: list[np.ndarray]) -> float:
    return float(unary_union([Polygon(p) for p in polys if len(p) >= 3]).area)


def sheet_box() -> Polygon:
    return sbox(0, 0, 210, 140)
