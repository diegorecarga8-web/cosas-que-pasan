# Formato del guion (`proyectos/<slug>/guion.json`)

Ejemplo completo: [`plantillas/guion_ejemplo.json`](../plantillas/guion_ejemplo.json). Solo `titulo` y
`escenas` (cada una con `prompt`) son obligatorios; todo lo demás tiene valor por defecto.

## Nivel superior

| Campo | Tipo | Por defecto | Qué hace |
|---|---|---|---|
| `titulo` | texto | — | Título del video (y de la miniatura si no se indica otro). |
| `slug` | texto | del título | Nombre de archivo del video final. |
| `formato` | `horizontal` \| `vertical` | `horizontal` | 1920×1080 (16:9) o 1080×1920 (9:16). También define la proporción de Veo y de las imágenes. |
| `estilo_visual` | texto (inglés) | vacío | Se agrega al final de cada prompt visual para mantener un look común. |
| `evitar` | texto (inglés) | texto, subtítulos, logos… | Prompt negativo de Veo y de la hoja del modo app. |
| `video.modelo` | texto | `veo-3.1-lite-generate-preview` | Otras opciones: `veo-3.1-fast-generate-preview`, `veo-3.1-generate-preview`. |
| `video.resolucion` | `720p` \| `1080p` \| `4k` | `720p` | Resolución de Veo (el montaje final siempre sale a 1080p). |
| `imagen.modelo` | texto | `gemini-3.1-flash-image` | Modelo para las escenas de tipo imagen. |
| `voz.activar` | sí/no | sí si hay narración | Genera la voz de la narración. Sin voz, la narración se muestra como subtítulos. |
| `voz.modelo` | texto | `gemini-3.1-flash-tts-preview` | Modelo de voz (TTS). |
| `voz.voz` | texto | `Charon` | Voz prediseñada de Gemini (p. ej. `Kore`, `Puck`, `Charon`, `Fenrir`, `Aoede`, `Orus`, `Sulafat`). |
| `voz.indicaciones` | texto | narración intrigante, ritmo ágil | Cómo debe sonar la voz (se antepone al texto, en lenguaje natural). |
| `musica.archivo` | ruta | sin música | MP3/WAV relativo a la carpeta del proyecto; se repite y baja sola cuando hay voz. |
| `musica.volumen` | 0–1 | `0.15` | Volumen base de la música. |
| `subtitulos` | sí/no | `true` | Subtítulos de la narración. |
| `estilo.color_acento` | `#RRGGBB` | `#FFD23F` | Color de las palabras resaltadas y de la tarjeta de dato. |
| `estilo.mayusculas` | sí/no | `false` | Subtítulos en mayúsculas. |
| `gancho.texto` / `gancho.duracion` | texto / s | — / `3` | Frase grande al inicio, sobre la primera escena (con sacudida). |
| `cierre.texto` / `cierre.subtexto` / `cierre.duracion` | texto / texto / s | — / — / `3` | Tarjeta final sobre el último cuadro desenfocado. |
| `miniatura.texto` / `miniatura.escena` | texto / id | título / 1.ª escena | Miniatura 1280×720 (o 1080×1920 en vertical). |
| `shorts` | lista | ninguno | Ver abajo. |
| `metadata.descripcion` / `metadata.etiquetas` | texto / lista | — | Van a `entrega/metadata.txt`. |

## Escenas (`escenas[]`)

| Campo | Tipo | Por defecto | Qué hace |
|---|---|---|---|
| `id` | texto | `e01`, `e02`… | Identificador (nombre de archivos y de `--rehacer`). |
| `tipo` | `video` \| `imagen` | `video` | `video` = clip de Veo; `imagen` = imagen fija con movimiento (mucho más barata). |
| `prompt` | texto (inglés) | — | Descripción visual: sujeto, acción, lugar, cámara, luz. Sin texto en pantalla. |
| `narracion` | texto (español) | vacío | Lo que dice la voz. `*palabras*` se resaltan en los subtítulos (no se leen los asteriscos). |
| `duracion` | s | automática | Video: 4, 6 u 8 (lo que se paga a Veo); si falta, la más corta que cubre la narración. Imagen: segundos en pantalla (si falta, lo que dure la voz). |
| `mantener_clip` | sí/no | `false` | En video: no recortar el clip al largo de la narración. |
| `texto` | texto | — | Texto grande arriba (lugar, fecha). Admite `*resaltado*`. |
| `dato` | `{valor, etiqueta}` | — | Tarjeta con una cifra (p. ej. `{"valor": "+100", "etiqueta": "personas afectadas"}`). |
| `efecto` | `zoom_in` \| `zoom_out` \| `paneo_izq` \| `paneo_der` \| `ninguno` | `zoom_in` en imágenes | Movimiento de cámara para imágenes. En video, descríbelo en el prompt. |
| `sacudida` | sí/no | sí en la 1.ª escena si hay gancho | Sacudida de cámara al inicio de la escena (impacto). |
| `volumen_clip` | 0–1 | 0.3 con voz, 0.9 sin voz | Volumen del audio que genera Veo. |
| `imagen_inicial` | ruta o `@id` | — | Video que arranca desde una imagen (archivo del proyecto o la imagen generada de otra escena, p. ej. `"@e03"`). |
| `referencias` | lista de rutas | — | Hasta 3 imágenes de referencia (personaje, objeto) para mantener la consistencia en Veo. |
| `capitulo` | texto | — | Marca un capítulo de YouTube en `metadata.txt` (hacen falta 3+, de 10 s o más). |

## Shorts (`shorts[]`)

| Campo | Tipo | Por defecto | Qué hace |
|---|---|---|---|
| `titulo` | texto | `Short N` | Aparece en `metadata.txt`. |
| `escenas` | lista de ids | — | Escenas del guion que forman el short, en ese orden. |
| `gancho` | texto | — | Frase de entrada propia del short. |
| `encuadre` | `recorte` \| `relleno` | `recorte` | Si el video es horizontal: recortar al centro o encajar con fondo desenfocado. |

## Archivos del proyecto

```
proyectos/<slug>/
  guion.json          ← lo escribe Claude
  clips/  imagenes/   ← modo navegador/app: clips e imágenes de la app de Gemini (e01.mp4, e03.png…)
  voz/                ← opcional: tu propia grabación (e01.wav…)
  assets/             ← lo generado por la API (caché; fuera de git por defecto)
  render/             ← intermedios (se pueden borrar)
  entrega/            ← video final, short-N.mp4, miniatura.jpg, metadata.txt, PROMPTS_GEMINI_APP.md
  manifest.json       ← registro de lo generado y su costo estimado
  precios.json        ← opcional: corrige precios de precios.py para este proyecto
```
