"""Probetas de calibración (R0P): E1 (sujeción A), E4 (gancho) y escalera de holguras.

Las variantes B (entrada lateral) y C (lámina flexionada) de E1, y E5/E6/E9, quedan para la
segunda entrega de R0P (ver docs/experimentos.md).
"""

from __future__ import annotations

from pathlib import Path

from .export_3mf import shelf_pack, write_3mf
from .export_pdf import e2_template
from .params import Params, Profile
from .profile import Part, bar_part, tapa_part

E1_PROFILES = (
    ("convexa146", 146.0, True),
    ("concava146", 146.0, False),
    ("cerrada100", 100.0, True),
)


def e1_parts(p: Profile, length: float = 100.0, n_per_profile: int = 2) -> list[Part]:
    """E1, variante A: tiras de barra + tapa por cada perfil (convexo, cóncavo, cerrado)."""
    parts: list[Part] = []
    for label, phi, convex in E1_PROFILES:
        for k in range(1, n_per_profile + 1):
            parts.append(bar_part(length, phi, convex, p, f"E1A_{label}_{k}_barra"))
            parts.append(tapa_part(length, phi, convex, p, f"E1A_{label}_{k}_tapa", "costado"))
    return parts


def e4_parts(p: Profile, mode: str, seg: float = 15.0) -> list[Part]:
    """E4: pares barra+tapa cortos variando espesor de patilla, largo y holgura.
    mode 'pie' = patilla en Z (tapa invertida); 'costado' = patilla en el plano de capas."""
    parts: list[Part] = []
    for t in (0.8, 1.0, 1.2):
        for tip in (3.0, 4.0):
            for c in (0.2, 0.3):
                q = p.with_(patilla_t=t, clearance=c, tip_depth=tip)
                tag = f"E4_{mode}_t{t:.1f}_L{tip:.0f}_c{c:.1f}"
                parts.append(bar_part(seg, 180.0, True, q, tag + "_barra"))
                m = "invertida" if mode == "pie" else "costado"
                parts.append(tapa_part(seg, 180.0, True, q, tag + "_tapa", m))
    return parts


def ladder_parts(p: Profile, seg: float = 30.0) -> list[Part]:
    """Escalera de holguras de la ranura (0,2 / 0,3 / 0,4 mm por lado)."""
    parts: list[Part] = []
    for c in (0.20, 0.25, 0.30, 0.35, 0.40):
        q = p.with_(clearance=c)
        parts.append(bar_part(seg, 180.0, True, q, f"HOLGURA_c{c:.2f}_barra"))
        parts.append(tapa_part(seg, 180.0, True, q, f"HOLGURA_c{c:.2f}_tapa", "costado"))
    return parts


def generate_all(out: str | Path, params: Params | None = None) -> list[Path]:
    """Genera los 3MF de R0P en `out` y devuelve las rutas."""
    params = params or Params()
    p, pr = params.profile, params.printer
    sets = {
        "E1_A_sujecion": e1_parts(p),
        "E4_gancho_pie": e4_parts(p, "pie"),
        "E4_gancho_costado": e4_parts(p, "costado"),
        "E1_holguras": ladder_parts(p),
    }
    written: list[Path] = []
    for name, parts in sets.items():
        plates = shelf_pack(parts, pr.usable, pr.spacing)
        for i, plate in enumerate(plates, start=1):
            suffix = f"_placa{i}" if len(plates) > 1 else ""
            written.append(
                write_3mf(
                    Path(out) / f"{name}{suffix}.3mf",
                    plate,
                    title=f"{name} (parámetros {params.version})",
                )
            )
    written.append(e2_template(Path(out) / "E2_plantilla_triangulos.pdf", p))
    return written
