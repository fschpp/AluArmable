"""Tabla de mediciones en vivo de un modelo (§4.1, §4.2): lo que se muestra al abrirlo."""

from __future__ import annotations

import numpy as np

from .mesh_io import Mesh, components


def tri_min_angles(mesh: Mesh) -> np.ndarray:
    """Ángulo mínimo de cada triángulo, en grados."""
    p = mesh.vertices[mesh.faces]
    a = np.linalg.norm(p[:, 1] - p[:, 2], axis=1)
    b = np.linalg.norm(p[:, 2] - p[:, 0], axis=1)
    c = np.linalg.norm(p[:, 0] - p[:, 1], axis=1)

    def ang(x, y, z):  # ángulo opuesto al lado x
        return np.degrees(np.arccos(np.clip((y * y + z * z - x * x) / (2 * y * z), -1, 1)))

    A, B = ang(a, b, c), ang(b, a, c)
    return np.minimum(np.minimum(A, B), 180.0 - A - B)


ANGLE_BINS = (0, 10, 15, 20, 25, 90)


def measure(mesh: Mesh) -> dict:
    e = mesh.edges
    L = np.linalg.norm(mesh.vertices[e[:, 0]] - mesh.vertices[e[:, 1]], axis=1)
    ang = tri_min_angles(mesh)
    hist = np.histogram(ang, bins=ANGLE_BINS)[0]
    return {
        "caras": len(mesh.faces),
        "aristas": len(e),
        "vertices": len(mesh.vertices),
        "euler": mesh.euler,
        "partes": components(mesh),
        "dimensiones_mm": [round(float(x), 1) for x in mesh.dimensions],
        "volumen_cm3": round(mesh.volume / 1000, 1),
        "area_laminas_cm2": round(float(mesh.areas.sum()) / 100, 1),
        "arista_min_mm": round(float(L.min()), 1),
        "arista_mediana_mm": round(float(np.median(L)), 1),
        "arista_max_mm": round(float(L.max()), 1),
        "largo_total_aristas_m": round(float(L.sum()) / 1000, 1),
        "angulo_min_grados": round(float(ang.min()), 1),
        "triangulos_por_angulo_min": {
            f"{ANGLE_BINS[i]}-{ANGLE_BINS[i + 1]}": int(n) for i, n in enumerate(hist)
        },
    }


def format_table(m: dict) -> str:
    rows = [
        ("Caras / aristas / vértices", f"{m['caras']} / {m['aristas']} / {m['vertices']}"),
        ("Euler (esfera = 2)", m["euler"]),
        ("Dimensiones X × Y × Z (mm)", " × ".join(str(x) for x in m["dimensiones_mm"])),
        ("Área total de lámina (cm²)", m["area_laminas_cm2"]),
        (
            "Arista mín / mediana / máx (mm)",
            f"{m['arista_min_mm']} / {m['arista_mediana_mm']} / {m['arista_max_mm']}",
        ),
        ("Largo total de aristas (m)", m["largo_total_aristas_m"]),
        ("Ángulo mínimo (°)", m["angulo_min_grados"]),
    ]
    for k, n in m["triangulos_por_angulo_min"].items():
        rows.append((f"Triángulos con ángulo mín {k}°", n))
    w = max(len(str(k)) for k, _ in rows)
    return "\n".join(f"{k:<{w}}  {v}" for k, v in rows)
