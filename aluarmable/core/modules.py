"""Módulos y cortes (R2b, §5.6 y §6.5): partir el modelo en módulos transportables.

Un módulo es un conjunto de paneles conexo; un corte es el conjunto de barras entre dos
módulos y debe formar lazos cerrados. Este núcleo sirve a la GUI (planos, pintar caras) y
valida cada corte con los controles del plan.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .params import Profile
from .pbn import PBN
from .sheets import root_radius

MAX_MODULE = 600.0  # tamaño máximo de un módulo (baúl del auto), mm
MAX_LOOP_NODES = 24  # aviso por encima de esto
CLOSURE_FREE = 16.0  # tramo libre mínimo alrededor de un nudo de cierre, mm
CLOSURES = (3, 6)  # mínimo y máximo de cierres de bayoneta por corte


@dataclass
class Module:
    name: str
    panels: list[int]
    size: float  # mayor dimensión del bbox, mm
    warnings: list[str] = field(default_factory=list)


@dataclass
class Cut:
    a: str
    b: str
    bars: list[int]
    loops: list[list[int]]  # nudos de cada lazo, en orden
    closed: bool
    perimeter: float
    planarity_rms: float
    planarity_max: float
    in_plane: tuple[float, float]
    apex: np.ndarray  # nudo apical: centroide del lazo
    axis: np.ndarray  # normal del plano ajustado
    closures: list[int]  # nudos elegidos para cierres de bayoneta
    warnings: list[str] = field(default_factory=list)

    @property
    def nodes(self) -> int:
        return sum(len(lp) for lp in self.loops)


@dataclass
class ModuleSplit:
    modules: list[Module]
    cuts: list[Cut]
    of_panel: list[str]

    def deficit(self, name: str) -> int:
        """Barras que faltan para que el módulo suelto sea isostático: N − 3h."""
        n = h = 0
        for c in self.cuts:
            if name in (c.a, c.b):
                n += c.nodes
                h += len(c.loops)
        return n - 3 * h

    def warnings(self) -> list[str]:
        return [w for m in self.modules for w in m.warnings] + [
            w for c in self.cuts for w in c.warnings
        ]


def panel_centroids(g: PBN) -> np.ndarray:
    return np.array([np.mean([g.nodes[i].pos for i in p.nodes], axis=0) for p in g.panels])


def assign_by(g: PBN, rule: Callable[[np.ndarray], str]) -> list[str]:
    """Nombre de módulo de cada panel según una regla sobre su centroide."""
    return [rule(c) for c in panel_centroids(g)]


def assign_by_plane(
    g: PBN, origin: np.ndarray, normal: np.ndarray, names: tuple[str, str] = ("A", "B")
) -> list[str]:
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    d = (panel_centroids(g) - np.asarray(origin, float)) @ n
    return [names[0] if x < 0 else names[1] for x in d]


def bisect(g: PBN, max_size: float = MAX_MODULE) -> list[str]:
    """Ayuda automática simple: biseca por la mediana de los centroides del eje más largo hasta
    que cada módulo mida ≤ `max_size`. Es un punto de partida; el usuario ajusta."""
    cen = panel_centroids(g)
    names = ["M1"] * len(g.panels)
    work = [(list(range(len(g.panels))), "M1")]
    count = 1
    while work:
        idx, name = work.pop()
        pts = np.array([g.nodes[i].pos for p in idx for i in g.panels[p].nodes])
        ext = np.ptp(pts, axis=0)
        if ext.max() <= max_size or len(idx) < 4:
            for p in idx:
                names[p] = name
            continue
        ax = int(np.argmax(ext))
        med = float(np.median(cen[idx, ax]))
        left = [p for p in idx if cen[p, ax] < med]
        right = [p for p in idx if cen[p, ax] >= med]
        if not left or not right:
            for p in idx:
                names[p] = name
            continue
        count += 1
        work.append((left, name))
        work.append((right, f"M{count}"))
    return names


def _loops(g: PBN, bars: list[int]) -> tuple[list[list[int]], bool]:
    """Ordena las barras de un corte en lazos de nudos. closed = todos los nudos tienen grado 2."""
    adj: dict[int, list[int]] = defaultdict(list)
    for bid in bars:
        b = g.bars[bid]
        adj[b.a].append(b.b)
        adj[b.b].append(b.a)
    closed = all(len(v) == 2 for v in adj.values())
    seen: set[int] = set()
    loops = []
    for start in sorted(adj):
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops, closed


def _plane_fit(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    n = vt[2]
    dist = (pts - c) @ n
    q = (pts - c) @ vt[:2].T
    return c, n, dist, q


def _min_box(q: np.ndarray) -> tuple[float, float]:
    best = None
    for ang in np.radians(np.arange(0.0, 180.0, 2.0)):
        c, s = math.cos(ang), math.sin(ang)
        r = q @ np.array([[c, -s], [s, c]])
        w, h = float(np.ptp(r[:, 0])), float(np.ptp(r[:, 1]))
        if best is None or w * h < best[0] * best[1]:
            best = (w, h)
    assert best is not None
    return max(best), min(best)


def _pick_closures(g: PBN, loop: list[int], prof: Profile) -> list[int]:
    """Nudos del lazo aptos (tramo libre de sus barras ≥ CLOSURE_FREE) y bien separados
    (muestreo del más lejano), hasta CLOSURES[1]."""
    ok = []
    for n in loop:
        frees = [
            g.bars[b].length
            - root_radius(g, g.bars[b].a, b, prof.W)
            - root_radius(g, g.bars[b].b, b, prof.W)
            for b in g.nodes[n].bars
        ]
        if min(frees) >= CLOSURE_FREE:
            ok.append(n)
    if not ok:
        return []
    pos = np.array([g.nodes[n].pos for n in ok])
    chosen = [0]
    while len(chosen) < min(CLOSURES[1], len(ok)):
        d = np.min(np.linalg.norm(pos[:, None] - pos[chosen][None], axis=2), axis=1)
        k = int(np.argmax(d))
        if d[k] < 40.0:  # demasiado juntos para repartir esfuerzos
            break
        chosen.append(k)
    return [ok[k] for k in chosen]


def split_modules(g: PBN, of_panel: list[str], prof: Profile | None = None) -> ModuleSplit:
    prof = prof or Profile()
    names = sorted(set(of_panel))
    modules = []
    for nm in names:
        pl = [i for i, m in enumerate(of_panel) if m == nm]
        pts = np.array([g.nodes[i].pos for p in pl for i in g.panels[p].nodes])
        mod = Module(nm, pl, float(np.ptp(pts, axis=0).max()))
        if mod.size > MAX_MODULE:
            mod.warnings.append(f"módulo {nm}: {mod.size:.0f} mm > {MAX_MODULE:.0f} mm")
        # conexo por barras no cortadas
        seen = {pl[0]}
        stack = [pl[0]]
        nb: dict[int, set[int]] = defaultdict(set)
        for b in g.bars:
            if of_panel[b.p1] == nm and of_panel[b.p2] == nm:
                nb[b.p1].add(b.p2)
                nb[b.p2].add(b.p1)
        while stack:
            for q in nb[stack.pop()]:
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        if len(seen) != len(pl):
            mod.warnings.append(f"módulo {nm}: no es conexo ({len(seen)} de {len(pl)} paneles)")
        modules.append(mod)
    by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
    for b in g.bars:
        ma, mb = of_panel[b.p1], of_panel[b.p2]
        if ma != mb:
            by_pair[tuple(sorted((ma, mb)))].append(b.id)  # type: ignore[arg-type]
    cuts = []
    for (a, b), bars in sorted(by_pair.items()):
        loops, closed = _loops(g, bars)
        nodes = sorted({n for lp in loops for n in lp})
        pts = np.array([g.nodes[n].pos for n in nodes])
        c, n_, dist, q = _plane_fit(pts)
        long_, short = _min_box(q)
        per = float(sum(g.bars[i].length for i in bars))
        warn = []
        if not closed:
            warn.append(f"corte {a}|{b}: no forma lazos cerrados")
        if len(nodes) > MAX_LOOP_NODES:
            warn.append(f"corte {a}|{b}: {len(nodes)} vértices (> {MAX_LOOP_NODES})")
        closures = []
        for lp in loops:
            closures += _pick_closures(g, lp, prof)
        if len(closures) < CLOSURES[0] * len(loops):
            warn.append(
                f"corte {a}|{b}: solo {len(closures)} nudos aptos para cierre (mín {CLOSURES[0]})"
            )
        cuts.append(
            Cut(
                a, b, bars, loops, closed, per,
                float(np.sqrt(np.mean(dist**2))), float(np.abs(dist).max()),
                (long_, short), c, n_, closures, warn,
            )
        )  # fmt: skip
    return ModuleSplit(modules, cuts, list(of_panel))
