# Registro de experimentos físicos

Plan completo en `PLAN_papercraft_aluminio_v3.md` §10. Cada fila se completa con: fecha, impresora y
filamento, parámetros usados, resultado de cada criterio, foto y qué valor del plan se cambió.

## Estado de la generación de probetas (R0P)

| Experimento | Archivos que genera `aluarmable-probes` | Estado |
|---|---|---|
| E1 variante A (tapa a presión) | `E1_A_sujecion.3mf`: barras + tapas de 100 mm, perfiles convexo 146°, cóncavo 146° y cerrado 100° (2 tiras por perfil) | generado, **sin imprimir** |
| E1 variantes B y C | — | pendiente (segunda entrega de R0P) |
| E1 holguras | `E1_holguras.3mf`: ranura con holgura 0,20 a 0,40 mm por lado | generado, sin imprimir |
| E2 corte a mano | `E2_plantilla_triangulos.pdf`: 10 triángulos (4×60, 4×100, 2×150 mm), regla de 100 mm | generado, sin imprimir |
| E3 alabeo | no necesita impresión: medir con vidrio | pendiente (cliente) |
| E4 gancho | `E4_gancho_pie.3mf` y `E4_gancho_costado.3mf`: espesor 0,8/1,0/1,2 × largo 3/4 × holgura 0,2/0,3 | generado, sin imprimir |
| E5, E6, E9 | — | pendiente (necesitan `node.py`, `lock.py`) |

Notas de diseño de las probetas (valores iniciales, los fija E1/E4):
- La patilla lleva un gancho de 0,25 mm de interferencia que encaja en una muesca de la pared de la ranura.
- «De pie» = patilla en el eje Z (tapa invertida); «de costado» = patilla en el plano de capas (tapa apoyada sobre su lado de 7 mm).
- Las tapas de E1 se imprimen de costado, porque su cara superior no es plana en perfiles no planos.
- Las pruebas verifican que la tapa asienta en la barra y no pisa la lámina de 0,11 mm; **no** verifican fuerzas ni PETG real.

## Resultados

_(vacío: todavía no se imprimió nada)_
