# Validacion de Equipos — video_836

## Asignacion tentativa (initial_side_fallback, x_norm)

| track_id | team tentativo | confianza | notas |
|---|---|---|---|
| robot_bt_01 | team_right | 0.64 | fallback by initial x_norm; split=0.585; value=0.693 |
| robot_bt_02 | team_left | 0.64 | fallback by initial x_norm; split=0.585; value=0.176 |
| robot_bt_03 | team_left | 0.64 | fallback by initial x_norm; split=0.585; value=0.585 |

## Instrucciones

1. Abre `robot_contactsheet.png` y compara los crops de cada robot.
2. Si la asignacion es correcta, escribe 'Confirmado' en el issue/respuesta.
3. Si necesitas corregir, edita `team_assignment.csv`:
   - Cambia el campo `team` de cada `track_id` al equipo correcto.
   - Usa exactamente `team_left` o `team_right` (u otro nombre consistente).
4. Vuelve a ejecutar este script con `--manual-assignment` apuntando al CSV editado.

## Metodo usado

Estrategia: `initial_side_fallback` — se asigna equipo basado en la posicion horizontal (x_norm) inicial del robot respecto al punto medio de todos los robots. **No es deteccion visual de uniformes.** Declarado como aproximacion heuristica.
