# Cosas que pasan — generación de video

Este repositorio es el destino para que la generación de video de **"Cosas que pasan"**
pueda correr en la nube (sesiones de Claude Code en la web/app), sin depender de que
tu computador esté encendido.

## Estado actual

- El pipeline real (skill de generación, scripts de descarga/render, imágenes
  descargadas) vive hoy **solo en tu computador**, en sesiones locales de Claude Code
  ("bridge"): *"Cosas que pasan"* y *"Eficiencia: imágenes vs animación en Cosas que
  pasan"*.
- Este repo todavía **no tiene ese contenido** — está vacío a propósito, como punto de
  partida para la migración.
- Mientras el contenido no se suba aquí, ninguna sesión en la nube tiene con qué
  trabajar (no hay imágenes, no hay skill, no hay scripts).

## Qué falta migrar

1. El **skill** de generación de video (donde esté hoy en tu máquina, normalmente
   `.claude/skills/cosas-que-pasan/`).
2. Los **scripts** de descarga de imágenes y de render (ffmpeg u otra herramienta).
3. Los **assets**: imágenes descargadas, fuentes, sonidos, plantillas.
4. La configuración de efectos ya afinada (hook phrase, data cards, camera shake,
   niveles de zoom/sonido, etc.).

Ver [`docs/migrar-a-la-nube.md`](docs/migrar-a-la-nube.md) para los pasos exactos.

## Objetivo final

Una vez migrado, cualquier sesión en la nube podrá:

- Clonar este repo con todo el pipeline y los assets ya incluidos.
- Generar el video sin que tu PC esté encendido ni conectado.
- Lanzarse desde el celular o la web, no solo desde tu computador.

Lo único que **no cambia**: el límite de uso (ventana de 5 horas) es de la cuenta
completa, no del repo ni de dónde corra la sesión — eso se comparte siempre.
