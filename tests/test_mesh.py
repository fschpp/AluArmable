import numpy as np
import pytest

from aluarmable.core import cleanup as cl
from aluarmable.core import measure, mesh_io
from aluarmable.core.mesh_io import Mesh, MeshError


def _cube() -> Mesh:
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float) * 100
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
    return Mesh(v, np.array(f), "cubo")


def _dog() -> Mesh:
    d = np.load("tests/data/dog650.npz")
    return mesh_io.validate(Mesh(d["V"].astype(float), d["F"].astype(int), "perro"))


def test_cube_valid_and_oriented():
    m = mesh_io.validate(_cube())
    assert m.euler == 2 and m.volume == pytest.approx(1e6)


def test_inward_faces_are_flipped():
    c = _cube()
    c.faces = c.faces[:, ::-1]
    m = mesh_io.validate(c)
    assert m.volume > 0 and any("orientación" in w for w in m.warnings)


def test_open_mesh_rejected_with_clear_message():
    c = _cube()
    c.faces = c.faces[:-1]
    with pytest.raises(MeshError, match="no es cerrado"):
        mesh_io.validate(c)


def test_duplicate_vertices_and_degenerates():
    c = _cube()
    v = np.vstack([c.vertices, c.vertices[:1]])
    f = np.vstack([c.faces, [[0, 0, 1]]])
    m = mesh_io.validate(Mesh(v, f))
    assert len(m.faces) == 12 and any("degenerados" in w for w in m.warnings)


def test_scale_to_height():
    m = mesh_io.scale_to_height(mesh_io.validate(_cube()), 500)
    assert m.dimensions[2] == pytest.approx(500) and m.vertices[:, 2].min() == 0


def test_load_stl_obj_roundtrip(tmp_path):
    import trimesh

    c = mesh_io.validate(_cube())
    t = trimesh.Trimesh(c.vertices, c.faces, process=False)
    for ext in ("stl", "obj"):
        p = tmp_path / f"c.{ext}"
        t.export(str(p))
        assert len(mesh_io.load(p).faces) == 12
    with pytest.raises(MeshError):
        mesh_io.load(tmp_path / "x.ply")


def test_dog_golden_values():
    m = measure.measure(_dog())
    assert (m["caras"], m["aristas"], m["vertices"]) == (650, 975, 327)
    assert m["euler"] == 2 and m["partes"] == 1
    assert m["dimensiones_mm"][2] == pytest.approx(1000, abs=1)
    assert "Caras" in measure.format_table(m)


@pytest.mark.slow
def test_cleanup_balanced_dog():
    dog = _dog()
    preset = cl.PRESETS["equilibrado"]
    out, _ = cl.cleanup(dog, preset.lmin, preset.angmin, preset.tol)
    assert 448 * 0.9 <= len(out.faces) <= 448 * 1.1
    assert out.euler == 2
    dev = cl.deviation(dog, out)
    assert dev["media"] == pytest.approx(2.3, rel=0.25) and dev["max"] <= 25.0
    assert (cl.failing_faces(dog), cl.failing_faces(out)) == (122, 8)
    assert cl.failing_faces(out) < cl.failing_faces(dog)


def test_cli_info_and_clean(tmp_path, capsys):
    import trimesh

    from aluarmable.cli import main

    d = np.load("tests/data/dog650.npz")
    p = tmp_path / "dog.stl"
    trimesh.Trimesh(d["V"].astype(float), d["F"], process=False).export(str(p))
    assert main(["info", str(p)]) == 0
    assert "650 / 975 / 327" in capsys.readouterr().out
    assert main(["info", str(tmp_path / "nada.stl")]) == 1
