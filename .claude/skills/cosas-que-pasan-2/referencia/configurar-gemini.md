# Conectar Cosas que pasan 2 con Gemini

## Primero, lo importante: plan vs. API

- **Tu plan Google AI Pro** ("Gemini Pro") sirve dentro de la app de Gemini y de Flow. Para video **no es
  ilimitado**: desde I/O 2026 la app usa una cuota de cómputo que se renueva cada 5 horas hasta un tope
  semanal, y generar video gasta bastante de esa cuota. Esa cuota no se puede usar desde un programa.
- **La API de Gemini** es lo que usa este pipeline para generar solo (Veo, imágenes y voz). Se cobra
  aparte, por uso. A cambio es automática, corre en la nube sin tu PC y no gasta tus límites de Claude
  manejando un navegador.
- **Puente entre ambos:** el plan Google AI Pro incluye US$10 al mes en créditos de Google Cloud (vía el
  Google Developer Program) que se pueden aplicar al uso de la API. Con Veo 3.1 Lite a 720p eso son
  ~200 s de video al mes.
- **Sin pagar API:** el modo app (`--videos app`) usa la cuota de tu plan: generas los clips en la app de
  Gemini con la hoja de prompts y el pipeline hace el montaje.

## 1. Crear la clave

1. Entra a <https://aistudio.google.com/apikey> con tu cuenta de Google (la misma del plan).
2. **Create API key** → elige o crea un proyecto de Google Cloud.
3. Veo, las imágenes y la voz requieren el **nivel de pago**: en AI Studio, en ese proyecto, activa la
   facturación (*Set up billing*). Sin facturación la API responde con error de cuota o de permisos.

## 2. Aplicar los créditos del plan (opcional, recomendado)

En <https://developers.google.com/program> revisa los beneficios de Google AI Pro, vincula tu perfil y
asigna los créditos mensuales al proyecto de Cloud de la clave. Los pasos exactos los define Google y
cambian seguido; si no aparecen, la API igual funciona con la facturación normal.

**Pon un tope de gasto:** en Google Cloud → Facturación → Presupuestos y alertas, crea un presupuesto
(por ejemplo US$10) con aviso por correo. El pipeline además estima el costo y pide confirmación antes
de gastar (`--confirmar`, `--max-usd`).

## 3. Guardar la clave (nunca en el chat ni en git)

- **Claude Code en la nube (web/app):** menú del entorno en la barra de título de la sesión → *Edit* →
  en *API credentials* (o variables de entorno) agrega `GEMINI_API_KEY` con tu clave. Las sesiones nuevas
  la reciben. El host `generativelanguage.googleapis.com` debe estar permitido en la red del entorno.
- **En tu PC:** crea un archivo `.env` en la raíz del repo con `GEMINI_API_KEY=tu_clave` (ya está en
  `.gitignore`) o define la variable de entorno en Windows.

## 4. Probar

```bash
python .claude/skills/cosas-que-pasan-2/cqp.py estimar proyectos/<slug>/guion.json
```

Para una prueba barata, un guion con una sola escena de video de 4 s cuesta ~US$0.20 con Veo 3.1 Lite.

## Modelos

Los modelos predeterminados (Veo 3.1 Lite, `gemini-3.1-flash-image`, `gemini-3.1-flash-tts-preview`) se
cambian por guion (`video.modelo`, `imagen.modelo`, `voz.modelo`). Los modelos 2.5 de Gemini se apagan el
16 de octubre de 2026: no los uses. Si Google retira o renombra un modelo, la API responde "not found":
cambia el id en el guion y, si cambia el precio, ajusta `cqp2/precios.py` o un `precios.json` del proyecto.
