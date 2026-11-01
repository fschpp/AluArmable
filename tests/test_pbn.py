import numpy as np
import pytest

from aluarmable.core import cleanup as cl
from aluarmable.core import mesh_io
from aluarmable.core.mesh_io import Mesh
from aluarmable.core.pbn import build_pbn


def _dog() -> Mesh:
    d = np.load("tests/data/dog650.npz")
    return mesh_io.validate(Mesh(d["V"].astype(float), d["F"].astype(int)))


def _cube(size=100.0) -> Mesh:
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) * size
    f = [
        (0, 1, 3),
        (0, 3, 2),
        (4, 6, 7),
        (4, 7, 5),
        (0, 4, 5),
        (0, 5, 1),
        (2, 3, 7),
        (2, 7, 6),
        (0, 2, 6),
        (0, 6, 4),
        (1, 5, 7),
        (1, 7, 3),
    ]
    return mesh_io.validate(Mesh(v, np.array(f)))


def test_cube_merges_to_six_quads():
    g = build_pbn(_cube())
    assert (len(g.nodes), len(g.bars), len(g.panels)) == (8, 12, 6)
    assert g.check() == [] and g.cuts == 0
    assert all(b.phi == pytest.approx(90) and b.convex for b in g.bars)


def test_cube_without_merge_has_diagonal_seams():
    g = build_pbn(_cube(), merge=False)
    assert (len(g.bars), len(g.panels)) == (18, 12) and g.check() == []
    assert sum(b.kind == "costura" for b in g.bars) == 0  # cada triángulo es su propia cara


def test_big_cube_is_split_with_seams():
    g = build_pbn(_cube(300))  # 300 mm no entra en 210 × 140
    assert g.cuts > 0 and g.check() == []
    assert any(b.kind == "costura" and b.phi == pytest.approx(180) for b in g.bars)
    assert any(n.kind == "costura-T" for n in g.nodes)
    labels = [p.label for p in g.panels]
    assert len(set(labels)) == len(labels)


def test_ids_are_stable_under_reload():
    a, b = build_pbn(_dog()), build_pbn(_dog())
    assert [n.pos.tolist() for n in a.nodes] == [n.pos.tolist() for n in b.nodes]
    assert [p.label for p in a.panels] == [p.label for p in b.panels]


def test_dog_original_golden():
    g = build_pbn(_dog(), merge=False)
    assert g.cuts == 78 and len(g.panels) == 728 and g.check() == []
    merged = build_pbn(_dog())  # la fusión de coplanares (tolerancia 1°) reduce piezas
    assert len(merged.panels) < 728 and merged.check() == []


def test_dog_clean_golden():
    d = _dog()
    pr = cl.PRESETS["equilibrado"]
    c, _ = cl.cleanup(d, pr.lmin, pr.angmin, pr.tol)
    g = build_pbn(c, merge=False)
    assert g.cuts == 78 and len(g.panels) == 526 and g.check() == []
    area = sum(p.area for p in g.panels) / 100
    # área de caras sin retranqueo (el 18.158 cm² del plan es la lámina ya retranqueada: R3)
    assert area == pytest.approx(c.areas.sum() / 100, rel=1e-6)
