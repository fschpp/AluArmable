import math

import numpy as np
import pytest
import trimesh
from manifold3d import CrossSection

from aluarmable.core.params import Profile
from aluarmable.core.profile import (
    bar_part,
    bar_section,
    step_angle,
    tapa_part,
    tapa_section,
    validate_profile,
)

CASES = [(146, True), (146, False), (100, True), (100, False), (180, True), (63, False)]


@pytest.mark.parametrize("phi,convex", CASES)
def test_parts_are_watertight(phi, convex):
    p = Profile()
    for part in (bar_part(50, phi, convex, p, "b"), tapa_part(50, phi, convex, p, "t")):
        m = trimesh.Trimesh(part.vertices, part.faces, process=False)
        assert m.is_watertight and m.is_winding_consistent
        assert m.volume > 0
        assert part.vertices[:, 2].min() == pytest.approx(0, abs=1e-9)


def test_step_angle():
    assert step_angle(180) == 0
    assert math.degrees(step_angle(146)) == pytest.approx(17.0)
    with pytest.raises(ValueError):
        step_angle(30)


@pytest.mark.parametrize("phi,convex", CASES)
def test_tapa_seats_without_covering_sheet(phi, convex):
    """La tapa solo interfiere con la barra en el gancho y deja libre la lámina (0,11 mm)."""
    p = Profile()
    bar, tapa = bar_section(phi, convex, p), tapa_section(phi, convex, p)
    inter = (bar - (bar - tapa)).area()
    assert inter < 2 * p.barb * p.barb_h * 1.5  # solo el gancho (dos lados)
    b = step_angle(phi)
    s = -1.0 if convex else 1.0
    for x0, x1 in ((p.e, p.W), (-p.W, -p.e)):
        ys = [s * math.tan(b) * abs(x) for x in (x0, x1)]
        sheet = CrossSection(
            [
                np.array(
                    [(x0, ys[0]), (x1, ys[1]), (x1, ys[1] + p.sheet_t), (x0, ys[0] + p.sheet_t)][
                        :: 1 if x1 > x0 else -1
                    ]
                )
            ]
        )
        sheet = (
            sheet
            if sheet.area() > 0
            else CrossSection(
                [
                    np.array(
                        [(x0, ys[0]), (x0, ys[0] + p.sheet_t), (x1, ys[1] + p.sheet_t), (x1, ys[1])]
                    )
                ]
            )
        )
        assert (sheet - (sheet - tapa)).area() < 1e-6
        assert (sheet - (sheet - bar)).area() < 1e-6


def test_default_profile_has_no_warnings():
    assert validate_profile(Profile()) == []
    assert validate_profile(Profile(patilla_t=0.6))
