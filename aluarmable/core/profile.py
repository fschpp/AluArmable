"""Sección de la barra, la tapa y la ranura; extrusión con manifold3d (§5.2).

Sistema de la sección: x a lo ancho, y hacia arriba, y = 0 en la arista. La barra se
extruye a lo largo de z y se reorienta a (largo = X, ancho = Y, arriba = Z).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from manifold3d import CrossSection, Manifold

from .params import Profile

PHI_MIN = 40.0
PHI_WARN = 45.0


@dataclass
class Part:
    """Pieza lista para exportar: malla triangular cerrada."""

    name: str
    vertices: np.ndarray  # (n, 3) float
    faces: np.ndarray  # (m, 3) int
    meta: dict | None = None

    @property
    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    @property
    def volume(self) -> float:
        v = self.vertices
        f = self.faces
        return float(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6)


def step_angle(phi: float) -> float:
    """Pendiente del escalón β = (180° − φ)/2, en radianes (Apéndice B.1)."""
    if not (PHI_MIN <= phi <= 180.0):
        raise ValueError(f"φ={phi}° fuera de [{PHI_MIN}, 180]")
    return math.radians((180.0 - phi) / 2.0)


def _poly(pts: list[tuple[float, float]]) -> CrossSection:
    a = np.array(pts, dtype=float)
    area = 0.5 * np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1])
    if area < 0:  # manifold espera contornos antihorarios
        a = a[::-1]
    return CrossSection([a])


def _rect(x0: float, y0: float, x1: float, y1: float) -> CrossSection:
    return _poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def bar_section(phi: float, convex: bool, p: Profile, slot_d: float | None = None) -> CrossSection:
    """Sección de la barra: cuerpo con dos escalones y ranura (con muesca) en el centro."""
    b = step_angle(phi)
    t = math.tan(b)
    s = -1.0 if convex else 1.0
    yw = s * t * p.W
    sd = p.slot_d if slot_d is None else slot_d
    h = max(p.H, sd + 1.5)
    bottom = -(h + (t * p.W if convex else 0.0))
    body = _poly([(-p.W, yw), (0.0, 0.0), (p.W, yw), (p.W, bottom), (-p.W, bottom)])
    hw = p.slot_w / 2
    slot = _rect(-hw, -sd, hw, 1.0)
    # muesca para el gancho, a la altura donde queda al asentar la tapa
    g_top = -(p.tip_depth - 0.2) if slot_d is None else -(sd - p.slot_floor - 0.2)
    g_bot = g_top - p.barb_h - 0.4
    gw = hw + p.groove
    groove = _rect(-gw, g_bot, gw, g_top)
    return body - slot - groove


def tapa_section(
    phi: float, convex: bool, p: Profile, tip_depth: float | None = None
) -> CrossSection:
    """Sección de la tapa: placa que sigue los escalones + patilla con gancho."""
    b = step_angle(phi)
    t = math.tan(b)
    s = -1.0 if convex else 1.0
    cb = math.cos(b)
    dv = (p.sheet_t + p.tapa_gap) / cb  # desplazamiento vertical de la cara inferior
    th = p.tapa_t / cb
    yw = s * t * p.W
    under = [(-p.W, yw + dv), (0.0, dv), (p.W, yw + dv)]
    top = [(p.W, yw + dv + th), (0.0, dv + th), (-p.W, yw + dv + th)]
    plate = _poly(under + top)
    td = p.tip_depth if tip_depth is None else tip_depth
    hp = p.patilla_t / 2
    stem = _rect(-hp, -td, hp, dv + 0.05)
    bb = hp + p.clearance + p.barb  # el gancho invade la pared de la ranura
    y1 = -td + 0.15
    y2 = y1 + p.barb_h
    barb = _poly(
        [
            (-hp, y1),
            (-bb, y1 + 0.15),
            (-bb, y2 - 0.3),
            (-hp, y2 + 0.3),
            (hp, y2 + 0.3),
            (bb, y2 - 0.3),
            (bb, y1 + 0.15),
            (hp, y1),
        ]
    )
    return plate + stem + barb


def _to_part(section: CrossSection, length: float, name: str, mode: str = "plana") -> Part:
    """Extruye y orienta. mode: 'plana' (sección tal cual, base abajo), 'invertida' (180° sobre
    el eje largo: patilla hacia arriba, «de pie»), 'costado' (90°: patilla en el plano de capas)."""
    if mode == "invertida":
        section = section.rotate(180.0)
    elif mode == "costado":
        section = section.rotate(-90.0)  # (x, y) -> (y, -x): patilla (0,-L) -> (-L, 0)
    elif mode != "plana":
        raise ValueError(mode)
    m = Manifold.extrude(section, length)
    me = m.to_mesh()
    v = np.asarray(me.vert_properties, dtype=float)[:, :3]
    f = np.asarray(me.tri_verts, dtype=int)
    v = v[:, [2, 0, 1]]  # (u, v, z_ext) -> (largo, ancho, arriba): permutación cíclica, det = +1
    v = v - v.min(axis=0)
    return Part(name=name, vertices=v, faces=f)


def bar_part(
    length: float, phi: float, convex: bool, p: Profile, name: str, slot_d: float | None = None
) -> Part:
    return _to_part(bar_section(phi, convex, p, slot_d), length, name, "plana")


def tapa_part(
    length: float,
    phi: float,
    convex: bool,
    p: Profile,
    name: str,
    mode: str = "costado",
    tip_depth: float | None = None,
) -> Part:
    return _to_part(tapa_section(phi, convex, p, tip_depth), length, name, mode)


def validate_profile(p: Profile) -> list[str]:
    """Chequeos de pared mínima y ranura mínima (§5.2). Devuelve avisos."""
    w: list[str] = []
    if p.W <= p.e:
        w.append("W <= e: la tapa no cubre la lámina")
    if p.slot_w < 1.0:
        w.append("ranura < 1,0 mm: no imprimible con boquilla 0,4")
    if p.patilla_t < 0.8:
        w.append("patilla < 0,8 mm: frágil (2 perímetros de 0,4)")
    wall = p.W - p.slot_w / 2 - p.groove
    if wall < 0.8:
        w.append(f"pared lateral junto a la muesca {wall:.2f} mm < 0,8 mm")
    return w
