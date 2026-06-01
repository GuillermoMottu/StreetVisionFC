# test_012_level2_metrics_video_836

## Configuracion

- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`.
- FPS: `59.707724425887264`.
- Resolucion/cancha usada: `1360.0x1808.0`.
- Umbral de posesion: `190.0px`.

## Resultados

- Frames observados: `61`.
- Tracks analizados: `4`.
- Tiempo observado aproximado: `1.021643s`.
- Tiempo con posesion asignada: `0.904406s`.
- Tiempo sin posesion asignada: `0.117238s`.

## Posesion Por Robot

- `robot_bt_01` (`neutral`): `0.904406s`, `88.52459%`, distancia media `152.989611px`.

## Posesion Por Equipo

- `neutral`: `0.904406s`, `88.52459%`.

## Supuestos

- Las metricas temporales usan los frames observados y los saltos de frame derivados del FPS.
- La posesion se asigna al robot mas cercano cuando el balon queda dentro del umbral configurado en pixeles.
- Distancia y velocidad son estimaciones en pixeles desde desplazamiento de centroides, no metros reales.

## Limitaciones

- La perspectiva de camara no esta rectificada; las distancias en pixeles varian con profundidad y angulo.
- Oclusiones, detecciones perdidas y cambios de ID pueden fragmentar distancia, velocidad y posesion.
- Las etiquetas de equipo quedan como unknown/neutral cuando el detector o tracker exporta clases neutrales.

## Artefactos

- `level2_metrics.csv`
- `level2_metrics.json`
- `config.yaml`
