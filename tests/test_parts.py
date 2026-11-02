import numpy as np
import pytest

from aluarmable.core import cleanup as cl
from aluarmable.core import mesh_io, parts, pbn
from aluarmable.core.mesh_io import Mesh
from tests.test_pbn import _cube


def test_cube_bars_and_plates(tmp_path):
    g = pbn.build_pbn(_cube(130))
    items = parts.make_bar_parts(g)
    assert len(items) == 12 and all(it.bar_part is not None for it in items)
    # una arista de 130 mm con raíces de 90° en ambos extremos
    assert items[0].free_length == pytest.approx(130 - 2 * parts.root_radius(g, 0, 0, 3.5))
    paths, est = parts.write_plates(items, tmp_path)
    assert paths and est["piezas"] == 24 and est["gramos"] > 0


def test_short_bar_warns():
    g = pbn.build_pbn(_cube(20))
    items = parts.make_bar_parts(g)
    assert any("tramo libre" in w for it in items for w in it.warnings)


def test_long_part_rotated_to_fit():
    g = pbn.build_pbn(_cube(300))
    it = next(i for i in parts.make_bar_parts(g) if i.bar_part is not None)
    q = parts.fit_on_bed(it.bar_part, (246.0, 246.0))
    assert np.ptp(q.vertices[:, 0]) <= 246 and np.ptp(q.vertices[:, 1]) <= 246


@pytest.mark.slow
def test_dog_clean_bars(tmp_path):
    d = np.load("tests/data/dog650.npz")
    dog = mesh_io.validate(Mesh(d["V"].astype(float), d["F"].astype(int)))
    pr = cl.PRESETS["equilibrado"]
    c, _ = cl.cleanup(dog, pr.lmin, pr.angmin, pr.tol)
    g = pbn.build_pbn(c, merge=False)
    items = parts.make_bar_parts(g)
    assert len(items) == len(g.bars) == 793
    bad = [it for it in items if it.bar_part is None]
    assert len(bad) <= 0.03 * len(items)
    _, est = parts.write_plates(items, tmp_path)
    assert 15 <= est["placas"] <= 60
