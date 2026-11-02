# AluArmable

Aplicación (Python + GTK4, Linux) para armar modelos 3D de pocas caras en **lámina de aluminio de lata**
sobre una **estructura impresa en 3D**, sin pegamento. Plan completo: [`docs/PLAN_papercraft_aluminio_v3.md`](docs/PLAN_papercraft_aluminio_v3.md).
Estado y pendientes: [`PROGRESS.md`](PROGRESS.md).

## Estado

Hecho: pista física **R0P** (probetas por consola) y el **núcleo de R1/R1b** (abrir, validar, medir y limpiar mallas). La GUI (R0 en adelante) no está hecha.

## Uso (probetas)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
aluarmable-probes -o out/probetas      # 3MF por placa (A1, 246×246 mm útiles) y PDF de la prueba E2
pytest && ruff check .
```

Imprimir en PETG, boquilla 0,4 mm, capas 0,16 mm, 3 a 4 perímetros. Los criterios de aprobado y cómo
registrar resultados están en [`docs/experimentos.md`](docs/experimentos.md).

## Uso (modelos)

```bash
aluarmable info perro.stl --altura 1000        # mediciones; avisa si la malla no es cerrada
aluarmable clean perro.stl --altura 1000 -o perro_limpio.stl --juego equilibrado
aluarmable pbn perro.stl --altura 1000 --sin-fusion   # paneles, barras, nudos, costuras
aluarmable sheets perro.stl --altura 1000 --limpiar equilibrado -o out/latas.pdf   # láminas en latas, PDF 1:1
```

```bash
aluarmable parts perro.stl --altura 1000 --limpiar equilibrado -o out/barras   # 3MF de barras y tapas
```

## Licencia

GPL-2.0 (ver `LICENSE`); la elección definitiva queda abierta (plan §15).
