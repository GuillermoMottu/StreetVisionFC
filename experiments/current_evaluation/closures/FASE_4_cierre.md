# Cierre de Fase 4 — Team Assignment y análisis semántico

## 1. Resumen de cambios

- **T1 (Ejecutar team_assignment):** `run_phase4_team_assignment.py` convierte
  `tracks_bytetrack.csv` → formato level3, ejecuta `build_team_assignment_package`
  con estrategia `initial_side_fallback` (eje x_norm), produce `team_assignment.csv`
  y `level3_tracks_video836.csv`.
- **Asignación validada por el usuario (humano en el loop):**
  - `robot_bt_01` → `team_right` (conf=0.64)
  - `robot_bt_02` → `team_left` (conf=0.64)
  - `robot_bt_03` → `team_left` (conf=0.64)
  - Confirmación: "Es correcta la asignación de equipos, continua con el desarrollo" (2026-06-13)
- **T2 (Conectar al pipeline):** `tracks_bytetrack_with_teams.csv` generado con
  columna `team` actualizada (146 filas de robot actualizadas). Demo video regenerado
  usando el nuevo CSV — tracking muestra colores distintos por equipo.
- **T3 (Documentar método):** declarado explícitamente como heurística de posición
  inicial, no detección visual de uniformes. `VALIDACION_EQUIPOS.md` documenta el
  método y cómo editarlo si cambia el clip.

## 2. Archivos creados

| Archivo | Descripción |
|---|---|
| `scripts/run_phase4_team_assignment.py` | Pipeline completo de asignación + contactsheet |
| `experiments/current_evaluation/phase4_team_assignment/level3_tracks_video836.csv` | Tracks convertidos a formato level3 |
| `experiments/current_evaluation/phase4_team_assignment/team_assignment.csv` | Asignación editable por track_id |
| `experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv` | Tracks con equipos aplicados (pipeline output) |
| `experiments/current_evaluation/phase4_team_assignment/robot_contactsheet.png` | Crops frame 142 para validación visual |
| `experiments/current_evaluation/phase4_team_assignment/VALIDACION_EQUIPOS.md` | Instrucciones y método documentado |
| `experiments/current_evaluation/phase4_team_assignment/team_assignment_summary.json` | Resumen JSON de estrategias y fuentes |

## 3. Resultados de asignación

| track_id | team | confianza | source | x_norm |
|---|---|---|---|---|
| robot_bt_01 | team_right | 0.64 | initial_side_fallback | 0.704 |
| robot_bt_02 | team_left | 0.64 | initial_side_fallback | 0.194 |
| robot_bt_03 | team_left | 0.64 | initial_side_fallback | 0.608 |

## 4. Estrategias evaluadas

| Estrategia | Estado | Confianza | Notas |
|---|---|---|---|
| `manual_by_id` | editable_template | 0.0 | CSV disponible para edición humana |
| `dominant_color` | not_available | 0.0 | Requiere crops/histogramas por robot — no disponibles |
| `initial_side_fallback` | available | 0.64 | Estrategia activa — split por x_norm inicial |

## 5. Conexión al pipeline (T2)

- `create_phase3_demo.py` actualizado: usa `tracks_bytetrack_with_teams.csv`
- Colores en demo: `team_right` = verde, `team_left` = azul
- Demo regenerado: `outputs/videos/futbotmx_demo_h264.mp4` (46.6 s, 2.4 MB)
- La sección de tracking ya muestra "Tracking con equipos" con leyenda de colores

## 6. Honestidad declarada (T3)

La asignación usa **posición horizontal inicial** (x_norm) como heurística de
separación. No detecta colores de uniforme ni usa ningún modelo visual. Confianza
declarada: 0.64 (no 1.0). Editable en cualquier momento vía `team_assignment.csv`.

## 7. Limitaciones conocidas

- `robot_bt_03` tiene solo 24 frames (aparece en 120-144 con gaps) — posiblemente
  entra y sale del campo de visión.
- La distribución visible es 1 vs 2 (bt_01 solo en team_right); si hay un segundo
  robot de team_right fuera del rango 120-180, no está capturado.
- `dominant_color` estrategia no disponible — requiere extracción de crops por robot
  con sus histogramas de color (trabajo futuro).
