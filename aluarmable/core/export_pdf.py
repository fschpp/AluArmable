"""PDF mínimo a escala 1:1 con pycairo. En R0P solo la plantilla de la prueba E2; las
plantillas de láminas del perro llegan con R3."""

from __future__ import annotations

import math
from pathlib import Path

import cairo

from .params import PARAMS_VERSION, Profile

MM = 72.0 / 25.4  # puntos por milímetro
A4 = (210.0, 297.0)


def inset_triangle(pts: list[tuple[float, float]], d: float) -> list[tuple[float, float]]:
    """Retranquea un triángulo `d` mm hacia adentro de cada lado (bisectrices)."""
    (ax, ay), (bx, by), (cx, cy) = pts
    a, b, c = (
        math.dist((bx, by), (cx, cy)),
        math.dist((ax, ay), (cx, cy)),
        math.dist((ax, ay), (bx, by)),
    )
    s = (a + b + c) / 2
    area = abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2
    r = area / s
    ix, iy = (a * ax + b * bx + c * cx) / (a + b + c), (a * ay + b * by + c * cy) / (a + b + c)
    k = (r - d) / r
    return [(ix + (x - ix) * k, iy + (y - iy) * k) for x, y in pts]


def _poly(ctx: cairo.Context, pts: list[tuple[float, float]]) -> None:
    ctx.move_to(pts[0][0] * MM, pts[0][1] * MM)
    for x, y in pts[1:]:
        ctx.line_to(x * MM, y * MM)
    ctx.close_path()


def e2_template(path: str | Path, p: Profile | None = None) -> Path:
    """10 triángulos equiláteros (4 de 60, 4 de 100 y 2 de 150 mm) con la línea de corte
    retranqueada e mm (cortar POR DENTRO de la línea), regla de 100 mm y versión de parámetros."""
    p = p or Profile()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    surf = cairo.PDFSurface(str(path), A4[0] * MM, A4[1] * MM)
    ctx = cairo.Context(surf)
    pages = [
        (60, [(15, 20), (95, 20), (15, 100), (95, 100)]),
        (100, [(20, 20), (20, 140)]),
        (100, [(20, 20), (20, 140)]),
        (150, [(20, 20), (20, 160)]),
    ]
    for page, (side, origins) in enumerate(pages, start=1):
        h = side * math.sqrt(3) / 2
        for ox, oy in origins:
            tri = [(ox, oy + h), (ox + side, oy + h), (ox + side / 2, oy)]
            ctx.set_source_rgb(0.6, 0.6, 0.6)
            ctx.set_line_width(0.3)
            ctx.set_dash([2, 2])
            _poly(ctx, tri)
            ctx.stroke()
            ctx.set_source_rgb(0, 0, 0)
            ctx.set_dash([])
            ctx.set_line_width(0.5)
            _poly(ctx, inset_triangle(tri, p.e))
            ctx.stroke()
            ctx.set_font_size(7)
            ctx.move_to((ox + side / 2 - 8) * MM, (oy + h * 0.7) * MM)
            ctx.show_text(f"{side} mm")
        # regla de 100 mm
        y = 285.0
        ctx.set_line_width(0.4)
        for i in range(0, 101, 10):
            ctx.move_to((20 + i) * MM, y * MM)
            ctx.line_to((20 + i) * MM, (y - (4 if i % 50 == 0 else 2.5)) * MM)
        ctx.move_to(20 * MM, y * MM)
        ctx.line_to(120 * MM, y * MM)
        ctx.stroke()
        ctx.set_font_size(7)
        ctx.move_to(20 * MM, (y + 5) * MM)
        ctx.show_text(
            f"Regla 100 mm: imprimir al 100 % (sin ajustar a la página). "
            f"E2 pág. {page}/4, parámetros {PARAMS_VERSION}, e = {p.e} mm"
        )
        ctx.move_to(20 * MM, (y + 9) * MM)
        ctx.show_text("Cortar POR DENTRO de la línea continua; la punteada es el borde de la cara.")
        ctx.show_page()
    surf.finish()
    return path
