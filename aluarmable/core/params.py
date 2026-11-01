"""Parámetros por defecto (Apéndice A del plan v3). Todo en milímetros y grados."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

PARAMS_VERSION = "v3.0"  # se imprime en cada plantilla/probeta


@dataclass(frozen=True)
class Profile:
    """Perfil de la barra, tapa y ranura (§5.2, §5.4)."""

    W: float = 3.5  # ancho del escalón a cada lado de la arista
    H: float = 5.5  # espesor mínimo del cuerpo bajo el escalón
    e: float = 1.5  # inicio de la lámina medido desde la arista
    sheet_t: float = 0.11  # espesor de la lámina de lata
    patilla_t: float = 0.9  # espesor de la patilla de la tapa
    clearance: float = 0.25  # holgura por lado patilla–ranura
    tip_depth: float = 3.2  # profundidad de la punta de la patilla bajo la arista
    slot_floor: float = 0.4  # material entre la punta y el fondo de la ranura
    tapa_t: float = 1.2  # espesor de la tapa
    tapa_gap: float = 0.3  # holgura escalón–tapa por encima de la lámina
    barb: float = 0.25  # interferencia del gancho contra la pared de la ranura
    groove: float = 0.35  # profundidad de la muesca en la pared de la ranura
    barb_h: float = 0.8  # alto del gancho

    @property
    def slot_w(self) -> float:
        return self.patilla_t + 2 * self.clearance

    @property
    def slot_d(self) -> float:
        return self.tip_depth + self.slot_floor

    def with_(self, **kw: float) -> Profile:
        return replace(self, **kw)


PROFILE_STANDARD = Profile()
PROFILE_LIGHT = Profile(W=3.0, H=4.5)
PROFILE_ROBUST = Profile(W=5.0, H=7.0)


@dataclass(frozen=True)
class Printer:
    """Perfil de impresora (Bambu Lab A1 por defecto)."""

    name: str = "Bambu Lab A1"
    bed: tuple[float, float] = (256.0, 256.0)
    usable: tuple[float, float] = (246.0, 246.0)
    nozzle: float = 0.4
    layer: float = 0.16
    spacing: float = 4.0  # separación entre piezas en la placa


@dataclass(frozen=True)
class Params:
    profile: Profile = field(default_factory=Profile)
    printer: Printer = field(default_factory=Printer)
    version: str = PARAMS_VERSION
