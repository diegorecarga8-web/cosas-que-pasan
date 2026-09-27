---
name: cosas-que-pasan-2
description: Produce videos de "Cosas que pasan 2" (video principal + shorts + miniatura + metadata para YouTube) generando los clips con Veo 3.1, las imágenes con Nano Banana y la narración con Gemini TTS a través de la API de Gemini, y montándolo todo con ffmpeg (gancho, tarjetas de datos, subtítulos, sacudida, música). Úsalo cuando pidan "cosas que pasan 2", "la v2 de cosas que pasan", un video de cosas que pasan con Gemini o Veo, o estimar/generar/renderizar un proyecto de proyectos/. Es un skill aparte: no toca ni reemplaza al skill "cosas-que-pasan" original (v1, con Google Flow).
---

# Cosas que pasan 2

Pipeline propio en esta carpeta (`cqp.py` + paquete `cqp2/`). Claude escribe el guion en JSON y el
pipeline hace el resto: genera lo que falta con la API de Gemini, lo guarda en caché (nunca paga dos
veces lo mismo) y arma los videos. Funciona igual en la nube y en el PC; no usa el navegador.

La v1 (skill `cosas-que-pasan`, Google Flow) sigue intacta: no la modifiques ni la mezcles con esta.

## Comandos

Ejecuta desde la raíz del repo (en otro lugar, usa la ruta de este skill en vez de `.claude/skills/cosas-que-pasan-2`):

```bash
CQP=".claude/skills/cosas-que-pasan-2/cqp.py"
python $CQP nuevo "Título del video" [--formato vertical]   # crea proyectos/<slug>/guion.json
python $CQP validar proyectos/<slug>/guion.json               # errores, avisos y línea de tiempo
python $CQP todo proyectos/<slug>/guion.json --simulado --borrador   # vista previa GRATIS
python $CQP estimar proyectos/<slug>/guion.json               # costo de lo que falta generar
python $CQP generar proyectos/<slug>/guion.json --confirmar   # genera con la API (cuesta dinero)
python $CQP render proyectos/<slug>/guion.json                # video, shorts, miniatura, metadata
python $CQP prompts proyectos/<slug>/guion.json               # hoja para el modo app
```

Dependencias: `pip install -r .claude/skills/cosas-que-pasan-2/requirements.txt` (en la nube lo hace
el hook de inicio). ffmpeg viene incluido en `imageio-ffmpeg`.

## Flujo de trabajo

1. **Investiga el tema** (WebSearch si está disponible). Usa solo hechos verificables: no inventes cifras,
   nombres ni fechas. Si algo es dudoso, formúlalo con prudencia ("se cree", "según…").
2. **Escribe el guion** con `nuevo` y reemplaza las escenas de la plantilla. Formato completo en
   [referencia/formato-guion.md](referencia/formato-guion.md). Sigue las reglas de abajo.
3. **Valida** y corrige errores y avisos (sobre todo los de duración: cada aviso es plata o ritmo).
4. **Vista previa gratis** si el usuario quiere revisar ritmo y textos: `todo --simulado --borrador`.
   Para revisarla tú, extrae fotogramas (`ffmpeg -ss 5 -i video.mp4 -frames:v 1 f.png`) y míralos.
5. **Estima y pide permiso.** Muestra la tabla de `estimar` y espera un sí explícito antes de gastar.
   Nunca uses `--confirmar` sin ese sí en esta conversación. Si el usuario dio un presupuesto
   ("hasta 5 dólares"), usa `--max-usd 5 --confirmar`.
6. **Genera.** Veo tarda 1–5 min por clip: ejecuta `generar` en segundo plano y espera el aviso. Si algo
   falla, lo demás queda guardado; vuelve a ejecutar y solo se reintenta lo que falta.
   Si Veo bloquea un prompt por seguridad, reformúlalo (sin personas reales, marcas ni violencia explícita).
7. **Renderiza** con `render` y revisa algunos fotogramas antes de entregar.
8. **Entrega.** En la nube, envía `entrega/*.mp4` y `entrega/miniatura.jpg` con SendUserFile y pega el
   contenido de `entrega/metadata.txt`. El contenedor de la nube es temporal: los clips pagados se
   pierden al cerrar la sesión. Si el usuario quiere poder re-editar después, ofrece subirlos al repo
   (`git add -f proyectos/<slug>/assets`; ~3–6 MB por clip).
9. **Cambios.** Editar el prompt de una escena regenera solo esa escena. Cambiar textos, gancho,
   subtítulos o música no regenera nada: solo `render`. Para repetir una escena igual: `--rehacer e03`.

## Reglas para el guion

- **Estructura:** gancho fuerte en los primeros 2–3 s → contexto → escalada → revelación → cierre.
  45–70 s para el video principal; los shorts toman 2–4 escenas (15–35 s) con su propio `gancho`.
- **Narración** (español, frases cortas, una idea por escena). A ~2.6 palabras/s: ≤9 palabras para un clip
  de 4 s, ≤14 para 6 s, ≤19 para 8 s. Si no pones `duracion`, se elige sola según la narración.
- **Prompts visuales en inglés**, concretos: sujeto + acción + lugar + movimiento de cámara + luz.
  Sin texto, logos ni personas reales. Describe igual a los personajes que se repiten (o usa `referencias`).
  El `estilo_visual` común se agrega solo a cada prompt; no lo repitas.
- **Imagen vs video:** usa `"tipo": "imagen"` (≈ $0.07, con zoom/paneo) para planos estáticos, lugares y
  objetos; reserva `"video"` (≈ $0.30–0.40 por clip con Veo Lite) para acción y movimiento real.
  Mezclar ambos baja mucho el costo sin que se note.
- **En pantalla:** `dato` para cifras, `texto` para lugar/fecha (no ambos en la misma escena).
  Resalta 1–3 palabras clave con `*asteriscos*` en gancho, narración o miniatura.
- **Formato:** `vertical` si el contenido es sobre todo para Shorts/Reels/TikTok; `horizontal` para el
  video principal de YouTube (los shorts se recortan en vertical; con 1080p quedan más nítidos).

## Modos (de dónde sale cada recurso)

| Modo | Qué hace | Costo |
|---|---|---|
| `--videos api` (predeterminado) | Veo 3.1 por la API de Gemini, automático | pago por segundo |
| `--videos app` | Usas la app de Gemini con el plan Google AI Pro: `prompts` crea la hoja, el usuario genera cada clip, lo guarda como `clips/e01.mp4`… y lo sube a la carpeta del proyecto | cuota del plan |
| `--simulado` | Marcadores con ffmpeg para revisar todo sin gastar | gratis |

`--imagenes` acepta lo mismo; `--voz` acepta `api`, `simulado` o `no`. Si el usuario deja su propia
grabación en `voz/e01.wav`, se usa esa. En modo app con `--voz api` solo se paga la voz (centavos).

Sobre "Gemini Pro ilimitado": el plan Google AI Pro **no** es ilimitado para video (desde I/O 2026 usa
una cuota de cómputo que se renueva cada 5 h hasta un tope semanal) y esa cuota solo sirve dentro de la
app, no para programas. La API se cobra aparte, aunque el plan incluye US$10 al mes en créditos de
Google Cloud que pueden pagar la API. Detalles y pasos en
[referencia/configurar-gemini.md](referencia/configurar-gemini.md).

## Costos aproximados (septiembre 2026, ver `cqp2/precios.py`)

Veo 3.1 Lite: US$0.05/s a 720p (clip de 8 s ≈ $0.40), $0.08/s a 1080p · Veo 3.1 Fast: ~$0.10/s ·
Veo 3.1: ~$0.40/s · imagen: ~$0.07 · voz: ~$0.03/min. Un video de ~1 min con 6 clips de Veo Lite
y 3 imágenes cuesta alrededor de US$2–3. `estimar` siempre da el número exacto antes de gastar.

## Si algo falla

- `Falta la clave de la API de Gemini`: el usuario debe agregar `GEMINI_API_KEY` como variable del entorno
  (nube) o en un `.env` (PC). Nunca le pidas que pegue la clave en el chat.
- 429 / cuota: baja `--paralelo 1` y reintenta más tarde; revisa que la facturación esté activa.
- Modelo no encontrado: cambia `video.modelo` / `imagen.modelo` / `voz.modelo` en el guion por uno vigente.
- Narración más larga que el clip: se congela el último cuadro; mejor subir `duracion` o dividir la escena.
