"""Limpieza de malla por colapso de aristas (QEM de Garland–Heckbert) con controles (§6.2, R1b).

Quita aristas cortas y triángulos agudos moviendo la superficie lo menos posible. Cada colapso
se rechaza si rompe la topología (condición de enlace), invierte o aplasta una cara, empeora un
triángulo ya agudo o si el error cuádrico supera la tolerancia.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .measure import tri_min_angles
from .mesh_io import Mesh


@dataclass(frozen=True)
class CleanupPreset:
    name: str
    lmin: float  # arista mínima (mm)
    angmin: float  # ángulo mínimo objetivo (°)
    tol: float  # error cuádrico rms admitido por colapso (mm)


# El perro a 1 m: 650 → ~574 / ~448 / ~392 caras (Apéndice D del plan)
PRESETS = {
    "conservador": CleanupPreset("conservador", 30.0, 20.0, 6.0),
    "equilibrado": CleanupPreset("equilibrado", 40.0, 25.0, 10.0),
    "economico": CleanupPreset("economico", 45.0, 25.0, 12.0),
}


def _min_angle(p: np.ndarray) -> float:
    a = np.linalg.norm(p[1] - p[2])
    b = np.linalg.norm(p[2] - p[0])
    c = np.linalg.norm(p[0] - p[1])
    if min(a, b, c) < 1e-9:
        return 0.0
    A = np.degrees(np.arccos(np.clip((b * b + c * c - a * a) / (2 * b * c), -1, 1)))
    B = np.degrees(np.arccos(np.clip((a * a + c * c - b * b) / (2 * a * c), -1, 1)))
    return min(A, B, 180 - A - B)


def _quadrics(V, F):
    Q = np.zeros((len(V), 4, 4))
    cnt = np.zeros(len(V))
    for f in F:
        p = V[list(f)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n = n / nn
        pl = np.append(n, -n @ p[0])
        K = np.outer(pl, pl)
        for v in f:
            Q[v] += K
            cnt[v] += 1
    return Q, cnt


def _try_collapse(V, F, vf, Q, cnt, a, b, tol, flipcos):
    fa, fb = vf[a], vf[b]
    shared = fa & fb
    if len(shared) != 2:
        return None
    na = {v for i in fa for v in F[i]} - {a}
    nb = {v for i in fb for v in F[i]} - {b}
    opp = {v for i in shared for v in F[i]} - {a, b}
    if ((na & nb) - {a, b}) != opp:  # condición de enlace: mantiene la variedad
        return None
    Qs = Q[a] + Q[b]
    n = cnt[a] + cnt[b]
    best = None
    for pos in (V[a], V[b], (V[a] + V[b]) / 2):
        vh = np.append(pos, 1.0)
        rms = np.sqrt(max(float(vh @ Qs @ vh), 0.0) / n)
        if best is None or rms < best[1]:
            best = (pos.copy(), rms)
    pos, rms = best
    if rms > tol:
        return None
    for i in (fa | fb) - shared:
        f = list(F[i])
        old = V[f]
        ids = [a if x == b else x for x in f]
        new = np.array([pos if x == a else V[x] for x in ids])
        n0 = np.cross(old[1] - old[0], old[2] - old[0])
        n1 = np.cross(new[1] - new[0], new[2] - new[0])
        l0, l1 = np.linalg.norm(n0), np.linalg.norm(n1)
        if l1 < 0.15 * l0 or float(n0 @ n1) / (l0 * l1) < flipcos:
            return None
        if _min_angle(new) < min(10.0, _min_angle(old)):
            return None
    return pos, rms


def cleanup(
    mesh: Mesh, lmin: float, angmin: float, tol: float, flipcos: float = 0.6, maxit: int = 3000
) -> tuple[Mesh, int]:
    """Devuelve (malla limpia, cantidad de colapsos). No modifica la entrada."""
    V = mesh.vertices.copy()
    F = [tuple(int(x) for x in f) for f in mesh.faces]
    Q, cnt = _quadrics(V, F)
    collapses = 0
    for _ in range(maxit):
        vf: dict[int, set[int]] = defaultdict(set)
        for i, f in enumerate(F):
            for v in f:
                vf[v].add(i)
        cand = []
        seen = set()
        for f in F:
            P = V[list(f)]
            ma = _min_angle(P)
            for k in range(3):
                a, b = f[k], f[(k + 1) % 3]
                key = (min(a, b), max(a, b))
                if key in seen:
                    continue
                seen.add(key)
                Lk = float(np.linalg.norm(V[a] - V[b]))
                if Lk < lmin:
                    cand.append((Lk / lmin, a, b))
            if ma < angmin:
                sides = sorted(
                    (float(np.linalg.norm(P[k] - P[(k + 1) % 3])), f[k], f[(k + 1) % 3])
                    for k in range(3)
                )
                cand.append((0.5 * ma / angmin, sides[0][1], sides[0][2]))
        cand.sort(key=lambda t: t[0])
        done = False
        for _, a, b in cand:
            for x, y in ((a, b), (b, a)):
                res = _try_collapse(V, F, vf, Q, cnt, x, y, tol, flipcos)
                if res is None:
                    continue
                pos, _ = res
                shared = vf[x] & vf[y]
                V[x] = pos
                Q[x] += Q[y]
                cnt[x] += cnt[y]
                F = [
                    tuple(x if t == y else t for t in f) for i, f in enumerate(F) if i not in shared
                ]
                collapses += 1
                done = True
                break
            if done:
                break
        if not done:
            break
    used = np.unique(np.array(F))
    remap = -np.ones(len(V), int)
    remap[used] = np.arange(len(used))
    out = Mesh(V[used], remap[np.array(F)], mesh.name, list(mesh.warnings))
    return out, collapses


def sample_surface(mesh: Mesh, n: int, rng: np.random.Generator) -> np.ndarray:
    ar = mesh.areas
    idx = rng.choice(len(ar), size=n, p=ar / ar.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    t = mesh.vertices[mesh.faces[idx]]
    return (
        (1 - s)[:, None] * t[:, 0] + (s * (1 - r2))[:, None] * t[:, 1] + (s * r2)[:, None] * t[:, 2]
    )


def deviation(original: Mesh, cleaned: Mesh, n: int = 250_000, seed: int = 0) -> dict:
    """Desvío de Hausdorff simétrico muestreado: media, p99 y máximo (mm)."""
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(seed)
    p0 = sample_surface(original, n, rng)
    p1 = sample_surface(cleaned, n, rng)
    d = np.concatenate([cKDTree(p0).query(p1)[0], cKDTree(p1).query(p0)[0]])
    return {"media": float(d.mean()), "p99": float(np.percentile(d, 99)), "max": float(d.max())}


def failing_faces(
    mesh: Mesh, w: float = 3.5, free_min: float = 12.0, visible_min: float = 0.25
) -> int:
    """Caras «que fallan» con el modelo de raíz simplificado de §6.3 (aprox. de R1b).

    Una cara falla si su inradio ρ deja menos de `visible_min` de lámina visible
    (((ρ − W)/ρ)² < visible_min) o si alguna de sus aristas queda con menos de `free_min` mm
    libres (largo − radios de raíz de ambos extremos).
    """
    V, F = mesh.vertices, mesh.faces
    e = mesh.edges
    nbr: dict[int, set[int]] = defaultdict(set)
    for a, b in e:
        nbr[a].add(b)
        nbr[b].add(a)

    def root(v: int, other: int) -> float:
        d0 = V[other] - V[v]
        d0 = d0 / np.linalg.norm(d0)
        th = 180.0
        for u in nbr[v]:
            if u == other:
                continue
            d1 = V[u] - V[v]
            d1 = d1 / np.linalg.norm(d1)
            th = min(th, float(np.degrees(np.arccos(np.clip(d0 @ d1, -1, 1)))))
        th = max(th, 5.0)
        return max(7.0, w / np.tan(np.radians(th) / 2) + 1.5)

    bad = 0
    for f in F:
        p = V[list(f)]
        a = np.linalg.norm(p[1] - p[2])
        b = np.linalg.norm(p[2] - p[0])
        c = np.linalg.norm(p[0] - p[1])
        s = (a + b + c) / 2
        area = np.sqrt(max(s * (s - a) * (s - b) * (s - c), 0.0))
        rho = area / s
        vis = ((rho - w) / rho) ** 2 if rho > w else 0.0
        short = any(
            np.linalg.norm(V[x] - V[y]) - root(x, y) - root(y, x) < free_min
            for x, y in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))
        )
        if vis < visible_min or short:
            bad += 1
    return bad


def summary(mesh: Mesh) -> dict:
    ang = tri_min_angles(mesh)
    return {"caras": len(mesh.faces), "angulo_min": float(ang.min()), "fallan": failing_faces(mesh)}
