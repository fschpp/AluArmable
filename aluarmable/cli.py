"""Línea de comandos: `aluarmable probes` / `aluarmable-probes`."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core import cleanup, export_pdf, measure, mesh_io, nesting, pbn, probes, sheets
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


def info_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="aluarmable info", description="Abre y mide un modelo.")
    ap.add_argument("modelo")
    ap.add_argument("--altura", type=float, help="tamaño final (mm) de la dimensión Z")
    args = ap.parse_args(argv)
    try:
        m = mesh_io.load(args.modelo)
    except mesh_io.MeshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.altura:
        m = mesh_io.scale_to_height(m, args.altura)
    for w in m.warnings:
        print(f"aviso: {w}")
    print(measure.format_table(measure.measure(m)))
    print(f"Caras que fallan (perfil estándar): {cleanup.failing_faces(m)}")
    return 0


def clean_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="aluarmable clean", description="Limpia la malla (R1b).")
    ap.add_argument("modelo")
    ap.add_argument("-o", "--out", required=True, help="STL de salida")
    ap.add_argument("--altura", type=float)
    ap.add_argument("--juego", choices=list(cleanup.PRESETS), default="equilibrado")
    args = ap.parse_args(argv)
    try:
        m = mesh_io.load(args.modelo)
    except mesh_io.MeshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.altura:
        m = mesh_io.scale_to_height(m, args.altura)
    pr = cleanup.PRESETS[args.juego]
    out, n = cleanup.cleanup(m, pr.lmin, pr.angmin, pr.tol)
    dev = cleanup.deviation(m, out)
    import trimesh

    trimesh.Trimesh(out.vertices, out.faces, process=False).export(args.out)
    print(f"{len(m.faces)} -> {len(out.faces)} caras ({n} colapsos); Euler {out.euler}")
    print(f"desvío (mm): media {dev['media']:.1f}, p99 {dev['p99']:.1f}, máx {dev['max']:.1f}")
    print(f"caras que fallan: {cleanup.failing_faces(m)} -> {cleanup.failing_faces(out)}")
    return 0


def pbn_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="aluarmable pbn", description="Inventario de paneles y barras."
    )
    ap.add_argument("modelo")
    ap.add_argument("--altura", type=float)
    ap.add_argument("--sin-fusion", action="store_true", help="no fusionar caras coplanares")
    args = ap.parse_args(argv)
    try:
        m = mesh_io.load(args.modelo)
    except mesh_io.MeshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.altura:
        m = mesh_io.scale_to_height(m, args.altura)
    g = pbn.build_pbn(m, merge=not args.sin_fusion)
    print(f"paneles {len(g.panels)}, barras {len(g.bars)}, nudos {len(g.nodes)} ", end="")
    print(f"({sum(n.kind == 'costura-T' for n in g.nodes)} T), cortes de costura {g.cuts}")
    print(f"Euler {g.euler}; invariantes: {g.check() or 'ok'}")
    return 0


def sheets_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="aluarmable sheets", description="Láminas, acomodo en latas y PDF 1:1."
    )
    ap.add_argument("modelo")
    ap.add_argument("-o", "--out", default="out/latas.pdf")
    ap.add_argument("--altura", type=float)
    ap.add_argument("--limpiar", choices=list(cleanup.PRESETS), help="limpiar la malla antes")
    args = ap.parse_args(argv)
    try:
        m = mesh_io.load(args.modelo)
    except mesh_io.MeshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.altura:
        m = mesh_io.scale_to_height(m, args.altura)
    if args.limpiar:
        pr = cleanup.PRESETS[args.limpiar]
        m, _ = cleanup.cleanup(m, pr.lmin, pr.angmin, pr.tol)
    g = pbn.build_pbn(m, merge=False)
    sh = sheets.make_sheets(g)
    cans = nesting.nest(sh)
    util = nesting.utilization(cans)
    export_pdf.cans_pdf(args.out, cans)
    print(f"{len(sh)} láminas ({sum(s.area for s in sh) / 100:.0f} cm²) en {len(cans)} latas")
    print(f"aprovechamiento {util:.0%}" + (" (bajo: < 70 %)" if util < 0.70 else ""))
    print(args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["probes"]:
        return probes_main(argv[1:])
    if argv[:1] == ["info"]:
        return info_main(argv[1:])
    if argv[:1] == ["sheets"]:
        return sheets_main(argv[1:])
    if argv[:1] == ["pbn"]:
        return pbn_main(argv[1:])
    if argv[:1] == ["clean"]:
        return clean_main(argv[1:])
    if argv[:1] == ["--version"]:
        print(__version__)
        return 0
    print("uso: aluarmable {probes|info|clean|pbn|sheets} ... (ver --help de cada uno)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
