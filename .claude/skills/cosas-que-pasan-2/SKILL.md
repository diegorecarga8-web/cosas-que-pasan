---
name: cosas-que-pasan-2
description: Produce videos de "Cosas que pasan 2" (video principal + shorts + miniatura + metadata para YouTube) con Gemini. Los clips de Veo salen de la app de Gemini usando la sesión de Google del usuario en su Chrome (modo navegador, sin clave, como la v1 con Flow) o de la API de Gemini, y se montan con ffmpeg (gancho, tarjetas de datos, subtítulos, sacudida, música). Úsalo cuando pidan "cosas que pasan 2", "la v2 de cosas que pasan", un video de cosas que pasan con Gemini o Veo, o generar/renderizar un proyecto de proyectos/. Es un skill aparte: no toca ni reemplaza al skill "cosas-que-pasan" original (v1, con Google Flow).
---

# Cosas que pasan 2

Pipeline propio en esta carpeta (`cqp.py` + paquete `cqp2/`). Claude escribe el guion en JSON, consigue
los clips de Gemini y el pipeline arma los videos.

La v1 (skill `cosas-que-pasan`, Google Flow) sigue intacta: no la modifiques ni la mezcles con esta.

## De dónde salen los clips: elige el modo

| Situación | Modo | Costo |
|---|---|---|
| Sesión en el PC del usuario con control de su Chrome (donde tiene iniciada su cuenta de Google con el plan AI Pro) | **navegador** (predeterminado si no hay clave): Claude genera cada clip en gemini.google.com, igual que la v1 hacía con Flow | gratis, gasta la cuota del plan |
| Hay `GEMINI_API_KEY` y el usuario aceptó el costo | **api**: Veo por la API de Gemini, sin navegador (sirve también en la nube) | pago por segundo |
| Nube sin clave | no se puede generar video real: gemini.google.com está bloqueado y no hay sesión de Google. Ofrece la vista previa `--simulado` y generar desde el PC (o configurar la clave) | — |

El plan Google AI Pro **no es ilimitado**: la app de Gemini usa una cuota de cómputo que se renueva cada
5 h hasta un tope semanal, y cada video gasta bastante. La API se cobra aparte (el plan trae US$10 al mes
en créditos de Google Cloud): ver [referencia/configurar-gemini.md](referencia/configurar-gemini.md).

## Comandos

Ejecuta desde la raíz del repo (en otro lugar, usa la ruta de este skill):

```bash
CQP=".claude/skills/cosas-que-pasan-2/cqp.py"
python $CQP nuevo "Título del video" [--formato vertical]   # crea proyectos/<slug>/guion.json
python $CQP validar proyectos/<slug>/guion.json               # errores, avisos y línea de tiempo
python $CQP todo proyectos/<slug>/guion.json --simulado --borrador   # vista previa GRATIS
# modo navegador
python $CQP siguiente proyectos/<slug>/guion.json             # qué escena toca y su prompt exacto
python $CQP recoger proyectos/<slug>/guion.json e01           # mueve la última descarga a clips/e01.mp4
python $CQP render proyectos/<slug>/guion.json --navegador    # video, shorts, miniatura, metadata
# modo api
python $CQP estimar proyectos/<slug>/guion.json               # costo de lo que falta generar
python $CQP todo proyectos/<slug>/guion.json --confirmar      # genera con la API y arma todo
```

Dependencias: `pip install -r .claude/skills/cosas-que-pasan-2/requirements.txt` (en la nube lo hace
el hook de inicio). ffmpeg viene incluido en `imageio-ffmpeg`.

## Flujo de trabajo

1. **Investiga el tema** (WebSearch si está disponible). Usa solo hechos verificables: no inventes cifras,
   nombres ni fechas. Si algo es dudoso, formúlalo con prudencia ("se cree", "según…").
2. **Escribe el guion** con `nuevo` y reemplaza las escenas de la plantilla. Formato completo en
   [referencia/formato-guion.md](referencia/formato-guion.md). Sigue las reglas de abajo.
3. **Valida** y corrige errores y avisos (sobre todo los de duración).
4. **Vista previa gratis** si el usuario quiere revisar ritmo y textos: `todo --simulado --borrador`.
   Para revisarla tú, extrae fotogramas (`ffmpeg -ss 5 -i video.mp4 -frames:v 1 f.png`) y míralos.
5. **Consigue los clips** con el modo que corresponda (secciones de abajo).
6. **Renderiza** (`render --navegador` o `render`) y revisa algunos fotogramas antes de entregar.
7. **Entrega** `entrega/*.mp4`, `entrega/miniatura.jpg` y el contenido de `entrega/metadata.txt`
   (en la nube, con SendUserFile). El contenedor de la nube es temporal: si el usuario quiere re-editar
   después, ofrece subir los clips al repo (`git add -f proyectos/<slug>/clips proyectos/<slug>/assets`).
8. **Cambios.** Cambiar textos, gancho, subtítulos o música no regenera clips: solo `render`.

## Modo navegador (sin clave, como la v1 con Flow)

Usa la herramienta que controla el Chrome del usuario (Claude in Chrome, la misma que la v1 usaba con
Flow). La cuenta de Google con el plan ya está iniciada ahí: no pidas contraseñas ni claves.

**Cuenta correcta:** el plan puede estar en otra cuenta de Google distinta de la principal del usuario.
Si existe `CQP2_CUENTA_GEMINI` (en el `.env` local; `siguiente` la muestra), esa es la cuenta a usar.
Antes del primer clip, confirma en Gemini la cuenta activa (foto de perfil, arriba a la derecha) y, si no
es la del plan, cámbiala ahí (o abre `gemini.google.com/u/1/app`, `/u/2/`…). Si esa cuenta no tiene
sesión iniciada en el Chrome, pide al usuario que la inicie él. No escribas el nombre de la cuenta en
archivos del repo: es público.

Ciclo, una escena a la vez:

1. `python $CQP siguiente proyectos/<slug>/guion.json` → te dice la escena, dónde va y el prompt exacto.
2. En <https://gemini.google.com/app> abre un chat nuevo. Para video elige la herramienta **Video**; para
   imagen basta el chat normal. Pega el prompt tal cual y envíalo.
3. Espera: un video tarda 1–3 min. Revisa cada ~30 s leyendo la página (texto o árbol de accesibilidad)
   en vez de pedir capturas seguidas: gasta mucho menos del uso de Claude.
4. Cuando aparezca, usa el botón de descarga de Gemini y espera a que termine la descarga.
5. `python $CQP recoger proyectos/<slug>/guion.json <id>` → mueve la descarga más reciente
   (de `~/Downloads`, o `--desde <carpeta>` / `--archivo <ruta>`) a `clips/` o `imagenes/`.
6. Repite hasta que `siguiente` diga "Nada pendiente". Luego `render proyectos/<slug>/guion.json --navegador`.

Reglas:
- Un clip a la vez, en una sola pestaña, a ritmo normal: no abras varias generaciones en paralelo.
- Si Gemini dice que se alcanzó el límite del plan, detente y avisa al usuario cuándo se renueva; lo
  descargado queda guardado y `siguiente` retoma donde quedó.
- Si Gemini rechaza un prompt, reformúlalo (sin personas reales, marcas ni violencia), actualízalo en el
  guion y vuelve a pedir `siguiente`.
- No importa si el clip sale de 8 s o con otra proporción: el render lo recorta al largo de la narración
  y al formato del video.
- **Voz:** sin clave no hay voz generada; la narración se muestra como subtítulos con tiempo de lectura.
  Si hay `GEMINI_API_KEY`, `--navegador` genera la voz por API (centavos) tras `generar --navegador --confirmar`.
  Si el usuario graba su voz en `voz/e01.wav`…, se usa esa.

## Modo api (automático, con clave)

1. `estimar` y muestra la tabla. Espera un sí explícito antes de gastar: nunca uses `--confirmar` sin ese
   sí en esta conversación. Con presupuesto dado ("hasta 5 dólares"): `--max-usd 5 --confirmar`.
2. `generar --confirmar` en segundo plano (Veo tarda 1–5 min por clip). Si algo falla, lo demás queda
   guardado; al volver a ejecutar solo se genera lo que falta. Nunca se paga dos veces la misma escena:
   editar el prompt de una escena regenera solo esa; `--rehacer e03` repite una igual.
3. Si Veo bloquea un prompt, reformúlalo. Luego `render`.

## Reglas para el guion

- **Antes de escribir, pregunta el tema** (y formato y duración si no los dijo). No elijas el tema por tu cuenta.
- **Estilo del canal: stick man.** Todos los videos van con monigotes (stick figures) en animación 2D simple.
  Usa siempre este `estilo_visual` (salvo que el usuario pida otro):
  `2D stick figure cartoon animation, simple black stick-figure characters with round heads and expressive
  faces, thick clean outlines, flat colors, minimal hand-drawn backgrounds, explainer video style`.
  En cada prompt nombra a las personas como stick figures ("a stick figure sailor", "a stick figure captain
  with a cap") con poses y caras expresivas, y fondos simples. Como monigotes se pueden mostrar personajes
  históricos (sin nombres escritos). El `evitar` por defecto ya excluye lo fotorrealista y el 3D.
- **Estructura:** gancho fuerte en los primeros 2–3 s → contexto → escalada → revelación → cierre.
  45–70 s para el video principal; los shorts toman 2–4 escenas (15–35 s) con su propio `gancho`.
- **Narración** (español, frases cortas, una idea por escena). A ~2.6 palabras/s: ≤9 palabras para un clip
  de 4 s, ≤14 para 6 s, ≤19 para 8 s. Si no pones `duracion`, se elige sola según la narración.
- **Prompts visuales en inglés**, concretos: sujeto + acción + lugar + movimiento de cámara.
  Sin texto ni logos. Describe igual a los personajes que se repiten (o usa `referencias`).
  El `estilo_visual` común se agrega solo a cada prompt; no lo repitas.
- **Imagen vs video:** usa `"tipo": "imagen"` (con zoom/paneo) para planos estáticos, lugares y objetos, y
  reserva `"video"` para acción y movimiento real. En modo navegador ahorra cuota del plan; en modo api,
  dinero (≈ $0.07 por imagen vs ≈ $0.30–0.40 por clip con Veo Lite).
- **En pantalla:** `dato` para cifras, `texto` para lugar/fecha (no ambos en la misma escena).
  Resalta 1–3 palabras clave con `*asteriscos*` en gancho, narración o miniatura.
- **Formato:** `vertical` si el contenido es sobre todo para Shorts/Reels/TikTok; `horizontal` para el
  video principal de YouTube (los shorts se recortan en vertical; con clips de 1080p quedan más nítidos).

## Otros modos de recursos

`--videos` / `--imagenes` aceptan `api`, `navegador` (= `app`: archivos en `clips/` e `imagenes/`) o
`simulado`; `--voz` acepta `api`, `simulado` o `no`. `prompts` escribe una hoja con todos los prompts por
si el usuario prefiere generarlos él mismo en la app y subirlos a `clips/` (por ejemplo desde el celular
con GitHub: Add file → Upload files).

## Costos aproximados del modo api (septiembre 2026, ver `cqp2/precios.py`)

Veo 3.1 Lite: US$0.05/s a 720p (clip de 8 s ≈ $0.40), $0.08/s a 1080p · Veo 3.1 Fast: ~$0.10/s ·
Veo 3.1: ~$0.40/s · imagen: ~$0.07 · voz: ~$0.03/min. Un video de ~1 min con 6 clips de Veo Lite
y 3 imágenes cuesta alrededor de US$2–3. `estimar` siempre da el número exacto antes de gastar.

## Si algo falla

- `Faltan recursos para: e01 (voz)`: genera la voz (`generar`) o renderiza con `--voz no` (subtítulos).
- `recoger` no encuentra la descarga: revisa que haya terminado; indica `--desde` o `--archivo`.
- `Falta la clave de la API de Gemini`: usa el modo navegador desde el PC, o que el usuario agregue
  `GEMINI_API_KEY` como variable del entorno (nube) o en un `.env` (PC). Nunca pidas la clave por el chat.
- 429 / cuota de la API: baja `--paralelo 1` y reintenta más tarde; revisa que la facturación esté activa.
- Modelo no encontrado: cambia `video.modelo` / `imagen.modelo` / `voz.modelo` en el guion por uno vigente.
