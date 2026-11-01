# AluArmable

Aplicación (Python + GTK4, Linux) para armar modelos 3D de pocas caras en **lámina de aluminio de lata**
sobre una **estructura impresa en 3D**, sin pegamento. Plan completo: [`docs/PLAN_papercraft_aluminio_v3.md`](docs/PLAN_papercraft_aluminio_v3.md).
Estado y pendientes: [`PROGRESS.md`](PROGRESS.md).

## Estado

Solo existe la pista física **R0P**: generador de probetas por consola. La GUI (R0 en adelante) no está hecha.

## Uso (probetas)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
aluarmable-probes -o out/probetas      # 3MF por placa (A1, 246×246 mm útiles) y PDF de la prueba E2
pytest && ruff check .
```

Imprimir en PETG, boquilla 0,4 mm, capas 0,16 mm, 3 a 4 perímetros. Los criterios de aprobado y cómo
registrar resultados están en [`docs/experimentos.md`](docs/experimentos.md).

## Licencia

GPL-2.0 (ver `LICENSE`); la elección definitiva queda abierta (plan §15).
