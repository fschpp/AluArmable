import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from aluarmable.core import export_pdf, mesh_io, nesting, pbn, sheets
from aluarmable.core.mesh_io import Mesh
from aluarmable.core.params import Profile


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


def _tetra(h_apex=100.0, base=100.0) -> Mesh:
    v = np.array(
        [[0, 0, 0], [base, 0, 0], [base / 2, base * 0.87, 0], [base / 2, base * 0.29, h_apex]],
        float,
    )
    f = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]
    return mesh_io.validate(Mesh(v, np.array(f)))


def test_cube_sheet_is_inset_and_chamfered():
    g = pbn.build_pbn(_cube())
    sh = sheets.make_sheets(g, Profile())
    assert len(sh) == 6
    for s in sh:
        assert s.area < 100 * 100  # retranqueo + esquinas cortadas
        assert s.area > (100 - 2 * 1.5 - 2 * 10) ** 2  # pero no desaparece
        assert s.up is None or abs(np.linalg.norm(s.up) - 1) < 1e-6


def test_sharp_tip_is_trimmed():
    # triángulo muy agudo: base 100, altura 100 en un tetraedro alto y angosto
    m = _tetra(h_apex=200.0, base=30.0)
    g = pbn.build_pbn(m, merge=False)
    sh = sheets.make_sheets(g)
    assert sum(s.trimmed for s in sh) > 0
    for s in sh:
        assert Polygon(s.poly).is_valid


def test_sheet_inside_face():
    g = pbn.build_pbn(_cube())
    for s in sheets.make_sheets(g):
        assert Polygon(s.face).buffer(1e-6).contains(Polygon(s.poly))


def test_nesting_no_overlap_and_inside_can():
    g = pbn.build_pbn(_cube(120), merge=False)
    sh = sheets.make_sheets(g)
    cans = nesting.nest(sh)
    assert sum(len(c.items) for c in cans) == len(sh)
    box = Polygon([(0, 0), (210, 0), (210, 140), (0, 140)]).buffer(1e-6)
    for c in cans:
        polys = [Polygon(i.poly) for i in c.items]
        for p in polys:
            assert box.contains(p)
        for a in range(len(polys)):
            for b in range(a + 1, len(polys)):
                assert polys[a].distance(polys[b]) >= nesting.GAP - 1.5  # separación para cortar


def test_piece_too_large_is_reported():
    big = sheets.Sheet(
        "F1",
        np.array([[0, 0], [400, 0], [400, 300], [0, 300]], float),
        np.zeros((3, 2)),
        None,
        120000,
        0,
        0,
    )
    with pytest.raises(ValueError, match="no entra"):
        nesting.nest([big])


def test_pdf_pages(tmp_path):
    g = pbn.build_pbn(_cube(120), merge=False)
    cans = nesting.nest(sheets.make_sheets(g))
    p = export_pdf.cans_pdf(tmp_path / "latas.pdf", cans)
    assert p.read_bytes().startswith(b"%PDF")
    import re
    import shutil
    import subprocess

    if shutil.which("pdfinfo"):
        out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, check=True).stdout
        assert re.search(rf"Pages:\s+{len(cans)}\b", out), out


def test_root_radius_grows_with_sharp_angle():
    g = pbn.build_pbn(_tetra(200.0, 30.0), merge=False)
    radii = [sheets.root_radius(g, n.id, b, 3.5) for n in g.nodes for b in n.bars]
    assert max(radii) > 20 and min(radii) >= sheets.R_MIN
    assert math.isfinite(max(radii))


def test_pairing_builds_disjoint_pieces_and_nests():
    g = pbn.build_pbn(mesh_io.validate(_cube(150)), merge=False)
    sh = sheets.make_sheets(g)
    pieces = nesting.pair_sheets(sh)
    for pc in pieces:
        if len(pc.members) == 2:
            a, b = (Polygon(m[1]) for m in pc.members)
            assert a.distance(b) >= nesting.GAP - 1e-6 and not a.intersects(b)
            assert Polygon(pc.hull).area >= pc.area - 1e-6
    cans = nesting.nest(sh, pair=True)
    assert sum(len(c.items) for c in cans) == len(sh)
