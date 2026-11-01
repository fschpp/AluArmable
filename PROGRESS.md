# PROGRESS

_Última actualización: 2026-11-01 (noche)_

## Current Focus
R0P en curso: repo `fschpp/AluArmable` con esqueleto, perfil de barra/tapa, 3MF mínimo y generador de probetas (`aluarmable-probes`); falta que el cliente las imprima. Antes (contexto): plan v3 de `aluarmable` (app Python + GTK4 para modelos armables en lámina de aluminio con estructura impresa en 3D) refinado al máximo y revisado por un agente independiente; falta que el cliente confirme las decisiones abiertas de §16 antes de empezar R0P (probetas) y R0.

## Todo List

### [ ] Todo
- [ ] Cliente: confirmar tiempo total (~400 h vs 180–270 h aceptadas; escenarios B ≈ 235 h, C ≈ 205 h), limpieza a ~450 caras y perfil «estándar» (§16)
- [ ] Cliente: conseguir/medir latas e imprimir probetas R0P (E1–E4; luego E5, E6, E9)
- [ ] R0 Esqueleto vivo (spike GtkGLArea: no se pudo probar GTK4 en el entorno de análisis)
- [ ] R1 → R9 según §9 (R1b limpieza, R2/R2b costuras y módulos, R3 plantillas, R4–R7b piezas, R8 guía, R9 pulido)
- [ ] Verificar licencias/versiones marcadas en la revisión (libnest2d, hypothesis, Python 3.11 vs numpy/scipy fijados, Wayland/EGL)

### [/] In Progress
- [/] R0P segunda entrega: variantes B y C de E1, y E5/E6/E9 (necesitan `node.py` y `lock.py` mínimos)
- [/] Cliente: imprimir probetas E1A, holguras, E4 y plantilla E2 (`aluarmable-probes -o out/probetas`)
- [/] Entrega del plan v3 al cliente y recepción de respuestas a §16

### [x] Done
- [x] R0P primera entrega (2026-11-01): `params`, `profile` (barra, tapa, ranura con muesca), `export_3mf` (un 3MF por placa, reproducible), `probes` (E1 A, holguras, E4 pie/costado), `export_pdf` (plantilla E2), CLI, 20 pruebas y ruff en verde, README y `docs/experimentos.md`
- [x] Entrevista de análisis, plan v1 y revisión 2 (perro 1 m)
- [x] Investigación de estado del arte y verificación de referencias (A1, PyRigi, Fictiv, Printago; moderngl+GLArea no recuperable)
- [x] Mediciones: limpieza de malla (650→448 caras, desvío medio 2,3 mm, máx 20,5), costuras/latas, módulos, rigidez
- [x] Nudo como «raíces fusionadas» (no esfera), perfil de barra, umbrales de triángulos agudos derivados de W (≥25°)
- [x] Prototipo G1: 672 barras unidas con manifold3d en <1 s, sólido válido
- [x] Masa/tiempo realistas (~7 kg, ~400 h; B y C) y corrección de la masa de lámina (0,030 g/cm²)
- [x] Bayoneta rediseñada: cierres periféricos de media vuelta (cortes no planos ni circulares)
- [x] Flexión por peso propio (pórtico y cercha) y tirantes internos; requisito de rigidez de giro del nudo ≥ 10 N·m/rad (E6)
- [x] Plan v3 (~1.230 líneas, 3 diagramas Mermaid validados) y revisión independiente: corregidos orden de experimentos/rebanadas (R0P ampliada), hito M1 (solo láminas de prueba), E8, E7 a 80 °C, boquilla 0,6 mm, inventario, déficit N−3h

## Latest Blockers/Discoveries
- Push a GitHub: el entorno de Claude no tiene credenciales (el repo es público para leer, pero push exige token). Ver estado del commit abajo.
- Las dimensiones del gancho (barb 0,25 mm, muesca 0,35 mm) son valores iniciales míos, no del plan; E4 los fija. Nada de esto está probado con PETG real.
- Verificado en código: la tapa asienta en la barra, solo interfiere en el gancho y deja libre la lámina de 0,11 mm (φ = 63°–180°, convexo y cóncavo).
- Python del entorno 3.12 con numpy 2.4 / scipy 1.17 (el plan fijaba otras versiones; no bloquea).
- El tiempo total (~400 h con uniones, columna y base) supera lo aceptado; palancas en §13.2.
- Cifras «58 mm» y «1,4 mm» (malla original articulada) vienen de versiones previas de scripts (out7/out8); lo reproducible es out9–out12 (153 mm / 6,3 mm con 3 tirantes). Tratar como índice de blandura.
- `out6b.txt` (8 módulos) viene de una versión del script que no se conservó.
- GTK4/GtkGLArea sin probar en el sandbox; planes B (PyOpenGL) y C (cairo).
- Ruta del plan vigente: `/home/claude/PLAN_papercraft_aluminio_v3.md` (el antiguo `PLAN_papercraft_aluminio.md` es de solo lectura y quedó superado).
