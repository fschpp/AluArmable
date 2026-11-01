"""Exportador mínimo a 3MF estándar, un archivo por placa (estrategia A de §6.11).

Reproducible: piezas en el orden dado y fecha fija en el ZIP.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np

from .profile import Part

_FIXED_DATE = (2026, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    "</Relationships>"
)


def model_xml(placed: list[tuple[Part, tuple[float, float]]], title: str = "") -> str:
    """placed: lista de (pieza, (x, y)) con la esquina mínima de la pieza sobre la placa."""
    out = [
        (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="millimeter" xml:lang="es" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        )
    ]
    if title:
        out.append(f'<metadata name="Title">{escape(title)}</metadata>')
    out.append("<resources>")
    for i, (part, _) in enumerate(placed, start=1):
        out.append(f'<object id="{i}" type="model" name={quoteattr(part.name)}><mesh><vertices>')
        out.extend(f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in part.vertices)
        out.append("</vertices><triangles>")
        out.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in part.faces)
        out.append("</triangles></mesh></object>")
    out.append("</resources><build>")
    for i, (part, (px, py)) in enumerate(placed, start=1):
        lo, _ = part.bbox
        tx, ty, tz = px - lo[0], py - lo[1], -lo[2]
        out.append(
            f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.5f} {ty:.5f} {tz:.5f}"/>'
        )
    out.append("</build></model>")
    return "".join(out)


def write_3mf(
    path: str | Path, placed: list[tuple[Part, tuple[float, float]]], title: str = ""
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in (
            ("[Content_Types].xml", _CONTENT_TYPES),
            ("_rels/.rels", _RELS),
            ("3D/3dmodel.model", model_xml(placed, title)),
        ):
            zi = zipfile.ZipInfo(name, _FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    return path


def shelf_pack(
    parts: list[Part], usable: tuple[float, float], spacing: float
) -> list[list[tuple[Part, tuple[float, float]]]]:
    """Acomodo por estantes sobre placas de `usable`; devuelve una lista de placas.
    Las piezas se ordenan por alto decreciente (estable)."""
    order = sorted(range(len(parts)), key=lambda i: (-float(np.ptp(parts[i].vertices[:, 1])), i))
    plates: list[list[tuple[Part, tuple[float, float]]]] = []
    x = y = row_h = 0.0
    cur: list[tuple[Part, tuple[float, float]]] = []
    for i in order:
        part = parts[i]
        w = float(np.ptp(part.vertices[:, 0]))
        h = float(np.ptp(part.vertices[:, 1]))
        if w > usable[0] or h > usable[1]:
            raise ValueError(f"{part.name}: {w:.0f}x{h:.0f} no entra en {usable}")
        if x + w > usable[0]:
            x, y, row_h = 0.0, y + row_h + spacing, 0.0
        if y + h > usable[1]:
            plates.append(cur)
            cur, x, y, row_h = [], 0.0, 0.0, 0.0
        cur.append((part, (x, y)))
        x += w + spacing
        row_h = max(row_h, h)
    if cur:
        plates.append(cur)
    return plates
