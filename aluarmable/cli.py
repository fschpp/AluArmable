"""Línea de comandos: `aluarmable probes` / `aluarmable-probes`."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core import probes
from .core.params import PROFILE_LIGHT, PROFILE_ROBUST, PROFILE_STANDARD, Params


def probes_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="aluarmable-probes", description="Genera las probetas 3MF de calibración (R0P)."
    )
    ap.add_argument("-o", "--out", default="out/probetas", help="carpeta de salida")
    ap.add_argument("--perfil", choices=["estandar", "ligero", "robusto"], default="estandar")
    args = ap.parse_args(argv)
    prof = {"estandar": PROFILE_STANDARD, "ligero": PROFILE_LIGHT, "robusto": PROFILE_ROBUST}[
        args.perfil
    ]
    for path in probes.generate_all(args.out, Params(profile=prof)):
        print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["probes"]:
        return probes_main(argv[1:])
    if argv[:1] == ["--version"]:
        print(__version__)
        return 0
    print("uso: aluarmable probes [-o DIR] [--perfil estandar|ligero|robusto]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
