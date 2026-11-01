"""Grafo panel–barra–nudo (PBN): fuente única de verdad del modelo armable (§6.1, §6.4, R2).

Pasos: (1) fusionar caras coplanares, (2) partir con costuras las caras que no entran en la
hoja útil, (3) construir barras (aristas entre paneles) con su diedro y IDs estables.
"""

from __future__ import annotations

import math
import string
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .mesh_io import Mesh

SHEET = (210.0, 140.0)  # hoja útil de la lata aplanada (largo, ancho), mm
QUANT = 0.1  # cuantización de posiciones para IDs estables (mm)


@dataclass
class Node:
    id: int
    pos: np.ndarray
    kind: str  # 'vertice' | 'costura-T'
    bars: list[int] = field(default_factory=list)


@dataclass
class Panel:
    id: int
    label: str
    nodes: list[int]  # contorno antihorario visto desde afuera, incluye nudos T
    corners: list[int]  # nudos que son esquinas (los demás son T o colineales)
    src: int  # id de la cara original (fusionada) de la que sale
    normal: np.ndarray
    area: float


@dataclass
class Bar:
    id: int
    a: int
    b: int
    p1: int
    p2: int
    phi: float  # grados, 180 = plano
    convex: bool
    length: float
    kind: str  # 'arista' | 'costura'


@dataclass
class PBN:
    nodes: list[Node]
    panels: list[Panel]
    bars: list[Bar]
    cuts: int = 0
    unmerged: int = 0

    @property
    def euler(self) -> int:
        return len(self.nodes) - len(self.bars) + len(self.panels)

    def check(self) -> list[str]:
        """Invariantes de §6.1; devuelve la lista de violaciones (vacía = correcto)."""
        bad = []
        cnt: dict[int, int] = defaultdict(int)
        for b in self.bars:
            cnt[b.id] += 2 if b.p1 != b.p2 else 1
        for b in self.bars:
            if b.p1 == b.p2:
                bad.append(f"barra {b.id} con un solo panel")
        if self.euler != 2:
            bad.append(f"Euler = {self.euler}")
        for n in self.nodes:
            if n.kind == "costura-T":
                bs = [self.bars[i] for i in n.bars]
                if len(bs) < 3:
                    bad.append(f"nudo T {n.id} con {len(bs)} barras")
        return bad


# ---------------------------------------------------------------- geometría 2D de paneles
def _frame(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = np.zeros(3)
    for i in range(1, len(pts) - 1):
        n += np.cross(pts[i] - pts[0], pts[i + 1] - pts[0])
    n /= np.linalg.norm(n)
    u = pts[1] - pts[0]
    u = u - (u @ n) * n
    u /= np.linalg.norm(u)
    return n, u, np.cross(n, u)


def to_2d(pts: np.ndarray) -> np.ndarray:
    _, u, v = _frame(pts)
    d = pts - pts[0]
    return np.column_stack([d @ u, d @ v])


def min_box(p2: np.ndarray, step_deg: float = 1.0) -> tuple[float, float]:
    """Rectángulo girado de menor área que contiene el polígono: (lado largo, lado corto)."""
    best = None
    for ang in np.radians(np.arange(0.0, 180.0, step_deg)):
        c, s = math.cos(ang), math.sin(ang)
        q = p2 @ np.array([[c, -s], [s, c]])
        w, h = float(np.ptp(q[:, 0])), float(np.ptp(q[:, 1]))
        w, h = max(w, h), min(w, h)
        if best is None or w * h < best[0] * best[1]:
            best = (w, h)
    assert best is not None
    return best


def fits(pts: np.ndarray, sheet: tuple[float, float] = SHEET) -> bool:
    long_, short = min_box(to_2d(pts))
    return long_ <= sheet[0] + 1e-6 and short <= sheet[1] + 1e-6


# ---------------------------------------------------------------- fusión de coplanares
def merge_coplanar(mesh: Mesh, tol_deg: float = 1.0, sheet=SHEET) -> list[list[int]]:
    """Polígonos (listas de vértices, antihorarios) tras fusionar triángulos coplanares vecinos.

    Un grupo se fusiona solo si su borde es un único lazo y el polígono entra en la hoja.
    """
    V, F = mesh.vertices, mesh.faces
    tri = V[F]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    cos_tol = math.cos(math.radians(tol_deg))
    parent = list(range(len(F)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edge_f: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, f in enumerate(F):
        for k in range(3):
            a, b = int(f[k]), int(f[(k + 1) % 3])
            edge_f[(min(a, b), max(a, b))].append(i)
    for fl in edge_f.values():
        i, j = fl
        d = abs(float(nrm[i] @ (tri[j].mean(axis=0) - tri[i][0])))
        if float(nrm[i] @ nrm[j]) >= cos_tol and d < 0.05:
            parent[find(i)] = find(j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(F)):
        groups[find(i)].append(i)
    polys: list[list[int]] = []
    for g in groups.values():
        if len(g) > 1:
            loop = _boundary_loop(F, g)
            if loop is not None and fits(V[loop], sheet):
                polys.append(loop)
                continue
        polys.extend([int(a), int(b), int(c)] for a, b, c in F[g])
    return polys


def _boundary_loop(F: np.ndarray, group: list[int]) -> list[int] | None:
    nxt: dict[int, list[int]] = defaultdict(list)
    directed = set()
    for i in group:
        a, b, c = (int(x) for x in F[i])
        directed |= {(a, b), (b, c), (c, a)}
    for a, b in directed:
        if (b, a) not in directed:
            nxt[a].append(b)
    if not nxt or any(len(v) != 1 for v in nxt.values()):
        return None
    start = min(nxt)
    loop = [start]
    cur = nxt[start][0]
    while cur != start:
        loop.append(cur)
        cur = nxt[cur][0]
        if len(loop) > len(nxt):
            return None
    return loop if len(loop) == len(nxt) else None


# ---------------------------------------------------------------- construcción del PBN
def build_pbn(
    mesh: Mesh, sheet: tuple[float, float] = SHEET, merge: bool = True, tol_deg: float = 1.0
) -> PBN:
    V = [np.asarray(p, float) for p in mesh.vertices]
    kinds = ["vertice"] * len(V)
    polys = (
        merge_coplanar(mesh, tol_deg, sheet) if merge else [list(map(int, f)) for f in mesh.faces]
    )
    # paneles de trabajo: poly (todos los nudos), corners, src
    work = [{"poly": p, "corners": list(p), "src": i} for i, p in enumerate(polys)]
    for w in work:
        w["tri"] = len(w["poly"]) == 3
    done: list[dict] = []
    cuts = 0

    def pts(ids):
        return np.array([V[i] for i in ids])

    def midnode(poly, i0, i1) -> tuple[int, int]:
        """Nudo en el punto medio del lado entre las esquinas de posiciones i0 < i1 del contorno.
        Devuelve (id, posición en poly). Reusa un nudo T ya existente; si no, lo crea e inserta."""
        a, b = poly[i0], poly[i1]
        mid = (V[a] + V[b]) / 2
        for k in range(i0 + 1, i1):
            if np.linalg.norm(V[poly[k]] - mid) < 1e-6:
                return poly[k], k
        # el medio cae dentro del tramo (u, v) de nudos consecutivos
        for k in range(i0, i1):
            u, v = poly[k], poly[k + 1]
            seg = V[v] - V[u]
            t = float((mid - V[u]) @ seg) / float(seg @ seg)
            if 0 < t < 1 and np.linalg.norm(V[u] + t * seg - mid) < 1e-6:
                V.append(mid)
                kinds.append("costura-T")
                m = len(V) - 1
                poly.insert(k + 1, m)  # el panel actual recorre (u, v) en el mismo sentido
                for other in [*work, *done]:  # vecinos: recorren el tramo al revés (v, u)
                    op = other["poly"]
                    for q in range(len(op)):
                        if op[q] == v and op[(q + 1) % len(op)] == u:
                            op.insert(q + 1, m)
                            break
                return m, k + 1
        raise RuntimeError("no se encontró el punto medio en el lado")

    while work:
        w = work.pop()
        poly = w["poly"]
        if not w["tri"] or fits(pts(w["corners"])):
            done.append(w)
            continue
        c = w["corners"]
        sides = [np.linalg.norm(V[c[(i + 1) % 3]] - V[c[i]]) for i in range(3)]
        i = int(np.argmax(sides))
        ci, cj, ck = c[i], c[(i + 1) % 3], c[(i + 2) % 3]
        # rotar el contorno para empezar en la esquina ci
        r = poly.index(ci)
        poly[:] = poly[r:] + poly[:r]
        ij, ik = poly.index(cj), poly.index(ck)
        # asegurar el orden ci, cj, ck cíclico a lo largo del contorno
        assert 0 < ij < ik
        m, im = midnode(poly, 0, ij)
        ij, ik = poly.index(cj), poly.index(ck)
        p1 = poly[0 : im + 1] + poly[ik:]
        p2 = poly[im : ik + 1]
        cuts += 1
        work.append({"poly": p1, "corners": [ci, m, ck], "src": w["src"], "tri": True})
        work.append({"poly": p2, "corners": [m, cj, ck], "src": w["src"], "tri": True})
    return _finish(V, kinds, done, cuts, merge, mesh)


def _finish(V, kinds, done, cuts, merge, mesh) -> PBN:
    P = np.array(V)
    q = np.round(P / QUANT).astype(np.int64)
    order = sorted(range(len(P)), key=lambda i: tuple(q[i]))
    nid = {old: new for new, old in enumerate(order)}
    nodes = [Node(nid[o], P[o], kinds[o]) for o in order]

    # paneles: orden estable por centroide cuantizado
    def cen(w):
        return tuple(np.round(P[w["poly"]].mean(axis=0) / QUANT).astype(np.int64))

    done.sort(key=cen)
    src_order: dict[int, int] = {}
    for w in done:
        src_order.setdefault(w["src"], len(src_order) + 1)
    per_src: dict[int, int] = defaultdict(int)
    count = defaultdict(int)
    for w in done:
        count[w["src"]] += 1
    panels = []
    for k, w in enumerate(done):
        poly = [nid[i] for i in w["poly"]]
        pts = np.array([nodes[i].pos for i in poly])
        n, _, _ = _frame(pts)
        area = float(
            0.5
            * np.linalg.norm(
                sum(np.cross(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
            )
        )
        lab = f"F{src_order[w['src']]}"
        if count[w["src"]] > 1:
            lab += "-" + string.ascii_lowercase[per_src[w["src"]] % 26] * (
                1 + per_src[w["src"]] // 26
            )
            per_src[w["src"]] += 1
        panels.append(Panel(k, lab, poly, [nid[i] for i in w["corners"]], w["src"], n, area))
    # barras
    edge_p: dict[tuple[int, int], list[int]] = defaultdict(list)
    for p in panels:
        for i in range(len(p.nodes)):
            a, b = p.nodes[i], p.nodes[(i + 1) % len(p.nodes)]
            edge_p[(min(a, b), max(a, b))].append(p.id)
    bars = []
    for (a, b), pl in sorted(edge_p.items()):
        if len(pl) != 2:
            raise ValueError(f"arista ({a},{b}) con {len(pl)} paneles: malla no cerrada")
        p1, p2 = panels[pl[0]], panels[pl[1]]
        n1, n2 = p1.normal, p2.normal
        ang = math.degrees(math.acos(float(np.clip(n1 @ n2, -1, 1))))
        phi = 180.0 - ang
        c2 = np.mean([nodes[i].pos for i in p2.nodes], axis=0)
        convex = bool(n1 @ (c2 - nodes[a].pos) <= 0)
        kind = "costura" if p1.src == p2.src else "arista"
        L = float(np.linalg.norm(nodes[a].pos - nodes[b].pos))
        bars.append(Bar(len(bars), a, b, p1.id, p2.id, phi, convex, L, kind))
        nodes[a].bars.append(bars[-1].id)
        nodes[b].bars.append(bars[-1].id)
    return PBN(nodes, panels, bars, cuts, 0)
