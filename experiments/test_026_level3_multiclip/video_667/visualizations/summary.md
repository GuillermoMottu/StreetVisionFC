# Visualizaciones Avanzadas Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_visualizations_v0.1`.
- Artefactos visuales indexados: `15`.
- Artefactos versionados: `15`.
- Highlights en storyboard: `3`.
- Grilla Voronoi: `24x16` (`384` celdas).

## Tipos De Asset

- `csv`: `1`.
- `png`: `14`.

## Familias

- `highlight`: `2`.
- `interaction`: `1`.
- `minimap`: `4`.
- `voronoi`: `8`.

## Cobertura

- Voronoi se renderiza en mini-mapa para frames representativos de `voronoi_frames.csv`.
- Cuando existe overlay ligero Nivel 2 y homografia, tambien se genera `voronoi_original_frame_*.png` sobre esa referencia.
- El grafo diferencia posesion, disputa, presion y proximidad con color y grosor por duracion/frecuencia.
- Los mini-mapas de highlights muestran trails, zona de actividad y etiqueta del evento.
- El storyboard combina referencia de frame Nivel 2, mini-mapa y texto conservador.

## Limitaciones

- Las proyecciones sobre frame original usan overlays ligeros existentes; no se abre ni versiona video completo.
- La homografia sigue siendo aproximada, por lo que Voronoi proyectado se trata como validacion visual, no medicion oficial.
- No se genero GIF; la secuencia queda como PNGs ligeros manifestados.

## Artefactos

- `config.yaml`
- `voronoi_frame_*.png`
- `voronoi_original_frame_*.png`
- `interaction_graph.png`
- `minimap_highlight_*.png`
- `highlight_storyboard.png`
- `highlight_storyboard_manifest.csv`
- `visualization_manifest.csv`
- `summary.md`

## Comando

```bash
.venv/bin/python scripts/run_level3_visualizations.py
```
