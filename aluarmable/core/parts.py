"""Piezas imprimibles de las barras (R4): barra con su perfil de escalón, tapa a presión,
largo libre entre raíces de nudo, avisos y acomodo en placas 3MF (§5.2, §5.3, §6.7)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .export_3mf import shelf_pack, write_3mf
from .params import Params, Profile
from .pbn import PBN
from .profile import PHI_MIN, Part, bar_part, tapa_part
from .sheets import root_radius

FREE_MIN = 12.0  # tramo libre mínimo de una barra (mm)
DENSITY = 1.27e-3  # g/mm³ (PETG)
FILL = 0.75  # fracción impresa (perímetros + relleno), valor central de §13.2
GRAMS_PER_HOUR = 18.0


@dataclass
class BarParts:
    bar: int
    label: str
    free_length: float
    bar_part: Part | None
    cap_part: Part | None
    warnings: list[str] = field(default_factory=list)


def rotate_z(part: Part, deg: float) -> Part:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    v = part.vertices.copy()
    x, y = v[:, 0].copy(), v[:, 1].copy()
    v[:, 0], v[:, 1] = c * x - s * y, s * x + c * y
    v -= v.min(axis=0)
    return Part(part.name, v, part.faces, part.meta)


def fit_on_bed(part: Part, usable: tuple[float, float]) -> Part:
    """Gira la pieza (0°, 90° o 45°) para que su huella entre en la placa."""
    for deg in (0.0, 90.0, 45.0):
        q = part if deg == 0 else rotate_z(part, deg)
        if np.ptp(q.vertices[:, 0]) <= usable[0] and np.ptp(q.vertices[:, 1]) <= usable[1]:
            return q
    raise ValueError(f"{part.name} no entra en la cama de {usable[0]:.0f} × {usable[1]:.0f} mm")


def make_bar_parts(g: PBN, prof: Profile | None = None) -> list[BarParts]:
    prof = prof or Profile()
    out: list[BarParts] = []
    for b in g.bars:
        label = f"E{b.id:03d}"
        ra = root_radius(g, b.a, b.id, prof.W)
        rb = root_radius(g, b.b, b.id, prof.W)
        free = b.length - ra - rb
        warn: list[str] = []
        if free < FREE_MIN:
            warn.append(f"{label}: tramo libre {free:.1f} mm < {FREE_MIN:.0f} mm")
        if b.phi < PHI_MIN:
            warn.append(f"{label}: diedro {b.phi:.1f}° < {PHI_MIN:.0f}° (no soportado)")
        if free <= 1.0 or b.phi < PHI_MIN:
            out.append(BarParts(b.id, label, free, None, None, warn))
            continue
        phi = min(b.phi, 180.0)
        out.append(
            BarParts(
                b.id,
                label,
                free,
                bar_part(free, phi, b.convex, prof, f"{label}_barra"),
                tapa_part(free, phi, b.convex, prof, f"{label}_tapa", "costado"),
                warn,
            )
        )
    return out


def estimate(parts: list[Part]) -> dict:
    vol = sum(p.volume for p in parts)
    grams = vol * DENSITY * FILL
    return {"piezas": len(parts), "gramos": grams, "horas": grams / GRAMS_PER_HOUR}


def write_plates(
    items: list[BarParts], out: str | Path, params: Params | None = None, name: str = "barras"
) -> tuple[list[Path], dict]:
    """Acomoda barras y tapas en placas de la A1 y escribe un 3MF por placa."""
    params = params or Params()
    pr = params.printer
    parts = [
        fit_on_bed(p, pr.usable)
        for it in items
        for p in (it.bar_part, it.cap_part)
        if p is not None
    ]
    plates = shelf_pack(parts, pr.usable, pr.spacing)
    paths = [
        write_3mf(
            Path(out) / f"{name}_placa{i:02d}.3mf", plate, title=f"{name} {i} ({params.version})"
        )
        for i, plate in enumerate(plates, start=1)
    ]
    est = estimate(parts)
    est["placas"] = len(plates)
    return paths, est
