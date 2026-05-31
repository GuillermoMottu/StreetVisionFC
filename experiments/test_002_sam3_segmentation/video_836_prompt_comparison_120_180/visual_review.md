# Visual review - prompt comparison

Revision manual ligera sobre overlays generados para frames `120`, `135`, `143`, `147`, `150` y `180`.

## Ball prompts

| Prompt | Precision visual | Nota |
|---|---|---|
| `ball` | Buena cuando detecta | Caja correcta sobre el balon en frames con deteccion. Pierde frames `135` y `147`. |
| `orange ball` | Buena cuando detecta | Resultado muy parecido a `ball`, con confianza media ligeramente menor. Pierde frames `135` y `147`. |
| `small orange ball` | Buena cuando detecta | Caja correcta, pero menor recall; tambien pierde frame `180`. |
| `soccer ball` | Mala | No produjo detecciones en los frames evaluados. |

Seleccion visual: `ball`.

## Robot prompts

| Prompt | Precision visual | Nota |
|---|---|---|
| `robot` | Buena | Detecta robots reales de cancha sin falsos positivos evidentes despues de ROI. |
| `soccer robot` | Buena | Similar a `robot`, con confianza media menor. |
| `wheeled robot` | Baja | Pierde varios frames y no cubre bien la estabilidad temporal. |
| `small robot` | Buena | Detecta robots reales de cancha en todos los frames revisados, con mayor recall y confianza media. |

Seleccion visual: `small robot`.

## Field prompts

| Prompt | Precision visual | Nota |
|---|---|---|
| `field` | Mala | No produjo detecciones. |
| `playing field` | Baja | Solo produjo una deteccion en la muestra. |
| `green soccer field` | Buena | Encierra la zona util de cancha en los overlays revisados; pierde frame `147`. |

Seleccion visual: `green soccer field`.

## Conclusion

Prompts base seleccionados para CopaFutMX: `green soccer field`, `small robot`, `ball`.
