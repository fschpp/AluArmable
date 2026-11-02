# PROGRESS

_Última actualización: 2026-11-01 (noche, 2.ª sesión)_

## Current Focus
R1/R1b (núcleo, sin GUI) hecho: abrir/validar/escalar modelos, tabla de mediciones y limpieza de malla con valores dorados del perro. Hecho también el núcleo de R2 (PBN y costuras). Hecho también el núcleo de R3 (láminas, acomodo y PDF de latas). Hecho el núcleo de R4 (barras y tapas en placas). Siguiente: R6 (nudos y raíces fusionadas; depende de E6), mejorar el acomodo (R3b: apareo de triángulos, objetivo ≥ 70 %), R2b (módulos y cortes) y la segunda entrega de R0P.

(Anterior) R0P en curso: repo `fschpp/AluArmable` con esqueleto, perfil de barra/tapa, 3MF mínimo y generador de probetas (`aluarmable-probes`); falta que el cliente las imprima. Antes (contexto): plan v3 de `aluarmable` (app Python + GTK4 para modelos armables en lámina de aluminio con estructura impresa en 3D) refinado al máximo y revisado por un agente independiente; falta que el cliente confirme las decisiones abiertas de §16 antes de empezar R0P (probetas) y R0.

## Todo List

### [ ] Todo
- [ ] Cliente: confirmar tiempo total (~400 h vs 180–270 h aceptadas; escenarios B ≈ 235 h, C ≈ 205 h), limpieza a ~450 caras y perfil «estándar» (§16)
- [ ] Cliente: conseguir/medir latas e imprimir probetas R0P (E1–E4; luego E5, E6, E9)
- [ ] R0 Esqueleto vivo (spike GtkGLArea: no se pudo probar GTK4 en el entorno de análisis)
- [ ] R0 (ventana GTK4 + visor) y las vistas de R1/R1b en la GUI: pendientes, GTK4 no instalable en este entorno
- [ ] R3b: mejorar aprovechamiento de latas (hoy 51 %, 113 latas; el 72 % del plan era un supuesto, no una medición; probé ángulos alineados a lados + contacto: 110 latas, no vale el costo; falta apareo de triángulos en paralelogramos)
- [ ] R2b, R4 → R9 según §9 (R1b limpieza, R2/R2b costuras y módulos, R3 plantillas, R4–R7b piezas, R8 guía, R9 pulido)
- [ ] Verificar licencias/versiones marcadas en la revisión (libnest2d, hypothesis, Python 3.11 vs numpy/scipy fijados, Wayland/EGL)

### [/] In Progress
- [/] R0P segunda entrega: variantes B y C de E1, y E5/E6/E9 (necesitan `node.py` y `lock.py` mínimos)
- [/] Cliente: imprimir probetas E1A, holguras, E4 y plantilla E2 (`aluarmable-probes -o out/probetas`)
- [/] Entrega del plan v3 al cliente y recepción de respuestas a §16

### [x] Done
- [x] R4 núcleo (2026-11-02): `parts.py` (barra con perfil de escalón y tapa por arista, tramo libre = largo − raíces, avisos de tramo < 12 mm y diedro < 40°, giro 90°/45° si no entra en la cama, acomodo en placas 3MF, estimación de gramos/horas), CLI `aluarmable parts`; perro limpio: 793 barras, 1578 piezas, 27 placas, 2,83 kg y ~157 h solo de barras y tapas; 7 barras con tramo libre corto y 4 con diedro de 39,5° (justo bajo el mínimo de 40°) para decidir; 46 pruebas en verde. **Aún sin nudos (R6): las barras no se pueden armar entre sí.**
- [x] R3 núcleo (2026-11-01): `sheets.py` (retranqueo e, esquinas cortadas por la raíz del nudo, puntas <25° recortadas a 8 mm, flecha «arriba»), `nesting.py` (acomodo por grilla de 1 mm y FFT, 4–8 orientaciones, separación 3 mm), `cans_pdf` (A4 apaisado, 1 lata por página, regla de 100 mm, versión de parámetros), CLI `aluarmable sheets`; perro limpio: 526 láminas, 16.929 cm², **113 latas, aprovechamiento 51 %** (rectángulos: ~147; objetivo del plan 86 latas / 72 %); 42 pruebas en verde
- [x] R2 núcleo (2026-11-01): `pbn.py` (grafo panel–barra–nudo, fusión de coplanares, costuras por arista más larga con nudos T reutilizados, diedro y convexa/cóncava, IDs estables, invariantes); perro original: 78 cortes, 728 paneles sin fusión; limpio: 526; CLI `aluarmable pbn`; 35 pruebas en verde
- [x] R1 + R1b núcleo (2026-11-01): `mesh_io` (STL/OBJ, validación con mensajes claros, orientación, escala), `measure` (tabla de §4.1), `cleanup` (QEM con controles; perro 650→448 caras, desvío medio 2,3 mm, máx 20,5; caras que fallan 122→8), CLI `aluarmable info|clean`, 29 pruebas en verde
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
