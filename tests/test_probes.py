import zipfile

import trimesh

from aluarmable.cli import probes_main
from aluarmable.core.export_3mf import shelf_pack, write_3mf
from aluarmable.core.params import Params
from aluarmable.core.probes import e1_parts, e4_parts, generate_all, ladder_parts


def test_generate_all_is_deterministic(tmp_path):
    a = generate_all(tmp_path / "a")
    b = generate_all(tmp_path / "b")
    assert [x.name for x in a] == [x.name for x in b]
    for x, y in zip(a, b):
        if x.suffix == ".3mf":
            assert x.read_bytes() == y.read_bytes()


def test_3mf_roundtrip(tmp_path):
    params = Params()
    parts = e1_parts(params.profile)
    plates = shelf_pack(parts, params.printer.usable, params.printer.spacing)
    path = write_3mf(tmp_path / "x.3mf", plates[0])
    with zipfile.ZipFile(path) as z:
        assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(z.namelist())
    scene = trimesh.load(path, force="scene")
    assert len(scene.geometry) == len(plates[0])
    for g in scene.geometry.values():
        assert g.is_watertight


def test_lib3mf_reads_files(tmp_path):
    lib3mf = __import__("pytest").importorskip("lib3mf")
    paths = [p for p in generate_all(tmp_path) if p.suffix == ".3mf"]
    wrapper = lib3mf.Wrapper()
    for p in paths:
        model = wrapper.CreateModel()
        model.QueryReader("3mf").ReadFromFile(str(p))


def test_plates_fit_bed():
    p = Params()
    for parts in (
        e1_parts(p.profile),
        e4_parts(p.profile, "pie"),
        e4_parts(p.profile, "costado"),
        ladder_parts(p.profile),
    ):
        for plate in shelf_pack(parts, p.printer.usable, p.printer.spacing):
            for part, (x, y) in plate:
                lo, hi = part.bbox
                assert x + (hi[0] - lo[0]) <= p.printer.usable[0] + 1e-6
                assert y + (hi[1] - lo[1]) <= p.printer.usable[1] + 1e-6


def test_e4_orientation_changes_footprint():
    p = Params().profile
    pie = e4_parts(p, "pie")[1]
    costado = e4_parts(p, "costado")[1]
    assert pie.vertices[:, 2].max() < 6  # de pie: la patilla crece en Z junto con la placa
    assert costado.vertices[:, 2].max() == __import__("pytest").approx(7.0, abs=0.01)  # ancho en Z


def test_cli(tmp_path):
    assert probes_main(["-o", str(tmp_path)]) == 0
    assert (tmp_path / "E2_plantilla_triangulos.pdf").exists()
