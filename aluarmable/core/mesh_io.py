"""Carga, validación y escala de modelos STL/OBJ (R1, §6.1 y §8)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


class MeshError(ValueError):
    """El modelo no sirve y el mensaje dice por qué (se muestra tal cual en la GUI)."""


@dataclass
class Mesh:
    vertices: np.ndarray  # (n, 3) float, milímetros
    faces: np.ndarray  # (m, 3) int
    name: str = "modelo"
    warnings: list[str] = field(default_factory=list)

    def copy(self) -> Mesh:
        return Mesh(self.vertices.copy(), self.faces.copy(), self.name, list(self.warnings))

    @property
    def edges(self) -> np.ndarray:
        e = np.sort(
            np.concatenate([self.faces[:, [0, 1]], self.faces[:, [1, 2]], self.faces[:, [2, 0]]]),
            axis=1,
        )
        return np.unique(e, axis=0)

    @property
    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    @property
    def dimensions(self) -> np.ndarray:
        lo, hi = self.bbox
        return hi - lo

    @property
    def euler(self) -> int:
        return len(self.vertices) - len(self.edges) + len(self.faces)

    @property
    def volume(self) -> float:
        v, f = self.vertices, self.faces
        return float(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6)

    @property
    def areas(self) -> np.ndarray:
        v, f = self.vertices, self.faces
        return 0.5 * np.linalg.norm(
            np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1
        )


def _merge_vertices(
    v: np.ndarray, f: np.ndarray, tol: float = 1e-6
) -> tuple[np.ndarray, np.ndarray]:
    scale = max(float(np.ptp(v, axis=0).max()), 1.0)
    q = np.round(v / (tol * scale)).astype(np.int64)
    _, idx, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    return v[idx], inv.reshape(-1)[f]


def validate(mesh: Mesh) -> Mesh:
    """Deja una malla cerrada, sin degenerados y con orientación hacia afuera.

    Arregla lo seguro (vértices duplicados, caras degeneradas, orientación global y por cara
    coherente) y levanta `MeshError` con un mensaje claro si no puede (malla abierta, arista
    compartida por más de dos caras, volumen nulo).
    """
    v, f = _merge_vertices(np.asarray(mesh.vertices, float), np.asarray(mesh.faces, int))
    warn = list(mesh.warnings)
    keep = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0])
    tri = v[f]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    keep &= area > 1e-9
    if (~keep).any():
        warn.append(f"se quitaron {int((~keep).sum())} triángulos degenerados")
        f = f[keep]
    if len(f) < 4:
        raise MeshError("El modelo tiene menos de 4 triángulos útiles.")
    used = np.unique(f)
    remap = -np.ones(len(v), int)
    remap[used] = np.arange(len(used))
    v, f = v[used], remap[f]
    # aristas dirigidas: en una malla cerrada y bien orientada cada una aparece 1 vez y su opuesta 1
    directed = Counter()
    for a, b, c in f:
        directed[(a, b)] += 1
        directed[(b, c)] += 1
        directed[(c, a)] += 1
    undirected = Counter()
    for (a, b), n in directed.items():
        undirected[(min(a, b), max(a, b))] += n
    open_e = [e for e, n in undirected.items() if n == 1]
    multi = [e for e, n in undirected.items() if n > 2]
    if open_e:
        raise MeshError(
            f"El modelo no es cerrado: {len(open_e)} aristas tienen una sola cara (agujeros). "
            "Cerrá los huecos en el programa de modelado y volvé a abrirlo."
        )
    if multi:
        raise MeshError(
            f"{len(multi)} aristas son compartidas por más de dos caras (geometría no variedad)."
        )
    if any(n > 1 for n in directed.values()):
        f = _orient_consistent(f)
    m = Mesh(v, f, mesh.name, warn)
    if m.volume < 0:
        m.faces = m.faces[:, ::-1].copy()
        warn.append("se invirtió la orientación de las caras (apuntaban hacia adentro)")
    if abs(m.volume) < 1e-6:
        raise MeshError("El volumen del modelo es nulo.")
    return m


def _orient_consistent(f: np.ndarray) -> np.ndarray:
    """Propaga una orientación coherente por adyacencia (BFS)."""
    f = f.copy()
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for i, (a, b, c) in enumerate(f):
        for x, y in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault((min(x, y), max(x, y)), []).append(i)
    seen = np.zeros(len(f), bool)
    for start in range(len(f)):
        if seen[start]:
            continue
        seen[start] = True
        stack = [start]
        while stack:
            i = stack.pop()
            a, b, c = f[i]
            for x, y in ((a, b), (b, c), (c, a)):
                for j in edge_faces[(min(x, y), max(x, y))]:
                    if j == i or seen[j]:
                        continue
                    p, q, r = f[j]
                    if (x, y) in ((p, q), (q, r), (r, p)):  # mismo sentido: invertir j
                        f[j] = (p, r, q)
                    seen[j] = True
                    stack.append(j)
    return f


def components(mesh: Mesh) -> int:
    parent = list(range(len(mesh.vertices)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, c in mesh.faces:
        parent[find(a)] = find(b)
        parent[find(b)] = find(c)
    return len({find(i) for i in np.unique(mesh.faces)})


def load(path: str | Path) -> Mesh:
    """Abre un STL u OBJ y lo valida. Las unidades se suponen milímetros."""
    import trimesh

    p = Path(path)
    if p.suffix.lower() not in (".stl", ".obj"):
        raise MeshError("Formato no soportado: usá STL u OBJ.")
    try:
        scene = trimesh.load(str(p), process=False, force="mesh")
    except Exception as exc:
        raise MeshError(f"No se pudo leer el archivo: {exc}") from exc
    if len(getattr(scene, "faces", [])) == 0:
        raise MeshError("El archivo no contiene triángulos.")
    mesh = validate(Mesh(np.asarray(scene.vertices, float), np.asarray(scene.faces, int), p.stem))
    n = components(mesh)
    if n > 1:
        mesh.warnings.append(f"el modelo tiene {n} partes separadas; se espera un solo sólido")
    return mesh


def scale_to_height(mesh: Mesh, height_mm: float, axis: int = 2) -> Mesh:
    """Escala uniforme para que la dimensión `axis` mida `height_mm`; apoya el modelo en z = 0."""
    if height_mm <= 0:
        raise MeshError("El tamaño final debe ser positivo.")
    out = mesh.copy()
    lo = out.vertices.min(axis=0)
    k = height_mm / float(np.ptp(out.vertices[:, axis]))
    out.vertices = (out.vertices - lo) * k
    return out
