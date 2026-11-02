import numpy as np
import pytest

from aluarmable.core import cleanup as cl
from aluarmable.core import mesh_io, modules, pbn
from aluarmable.core.mesh_io import Mesh
from tests.test_pbn import _cube


def dog_rule(c):
    x, y, z = c
    if y < 280 and z > 620:
        return "cabeza"
    if y > 1260 and z > 560:
        return "cola"
    if z < 320 and abs(x - 220) > 50:  # las patas no se tocan entre sí
        return ("pata_del" if y < 640 else "pata_tras") + ("_izq" if x < 220 else "_der")
    return "torso_del" if y < 640 else "torso_tras"


def _sphere():
    import trimesh

    t = trimesh.creation.icosphere(subdivisions=1, radius=100.0)
    t.apply_translation([0, 0, 100])
    return pbn.build_pbn(
        mesh_io.validate(Mesh(np.asarray(t.vertices), np.asarray(t.faces))), merge=False
    )


def _dog_graph():
    d = np.load("tests/data/dog650.npz")
    dog = mesh_io.validate(Mesh(d["V"].astype(float), d["F"].astype(int)))
    pr = cl.PRESETS["equilibrado"]
    c, _ = cl.cleanup(dog, pr.lmin, pr.angmin, pr.tol)
    return pbn.build_pbn(c, merge=False)


def test_sphere_plane_cut_makes_closed_loop():
    g = _sphere()
    of = modules.assign_by_plane(
        g, np.array([0, 0, 100.0]), np.array([0, 0, 1.0]), ("abajo", "arriba")
    )
    sp = modules.split_modules(g, of)
    assert {m.name for m in sp.modules} == {"abajo", "arriba"}
    (cut,) = sp.cuts
    assert cut.closed and len(cut.loops) == 1 and cut.planarity_rms < 25
    assert sp.deficit("abajo") == cut.nodes - 3
    assert not any("conexo" in w for w in sp.warnings())


def test_bisect_respects_max_size():
    g = _sphere()
    sp = modules.split_modules(g, modules.bisect(g, max_size=130))
    assert len(sp.modules) > 1 and all(m.size <= 130 + 1e-6 for m in sp.modules)


def test_disconnected_module_is_reported():
    g = pbn.build_pbn(_cube(120), merge=False)
    cen = modules.panel_centroids(g)
    of = ["A" if (c[0] < 60 and c[1] < 60) or (c[0] > 60 and c[1] > 60) else "B" for c in cen]
    sp = modules.split_modules(g, of)
    assert any("no es conexo" in w for w in sp.warnings()) or any(
        "cerrados" in w for w in sp.warnings()
    )


@pytest.mark.slow
def test_dog_eight_modules():
    g = _dog_graph()
    sp = modules.split_modules(g, modules.assign_by(g, dog_rule))
    assert len(sp.modules) == 8 and len(sp.cuts) in (7, 8, 9)
    assert all(c.closed and not c.warnings for c in sp.cuts)
    assert not any("conexo" in w for w in sp.warnings())
    # hallazgo: con 8 módulos los dos torsos miden ~760–790 mm, más que los 600 mm del plan
    big = {m.name for m in sp.modules if m.size > modules.MAX_MODULE}
    assert big == {"torso_del", "torso_tras"}
    assert all(sp.deficit(m.name) >= 3 for m in sp.modules)
    head = next(c for c in sp.cuts if {c.a, c.b} == {"cabeza", "torso_del"})
    assert head.perimeter == pytest.approx(2300, rel=0.1) or head.perimeter > 800
