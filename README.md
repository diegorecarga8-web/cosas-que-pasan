# Cosas que pasan

## Cosas que pasan 2 (Gemini / Veo)

Skill aparte en [`.claude/skills/cosas-que-pasan-2/`](.claude/skills/cosas-que-pasan-2/SKILL.md). Genera
el video principal, los shorts, la miniatura y la metadata de YouTube:

- **Clips de video** con Veo desde la **app de Gemini con tu sesión de Google** (modo navegador: sin clave,
  desde el PC, igual que la v1 hacía con Flow) o por la **API de Gemini** (automático, también en la nube;
  con imágenes de Nano Banana y narración de Gemini TTS).
- **Montaje** con ffmpeg: gancho animado, sacudida de cámara, zoom/paneo en imágenes, tarjetas de datos,
  subtítulos con palabras resaltadas, música que baja sola bajo la voz, cierre y volumen normalizado.
- **Caché y control de gasto:** estima el costo antes de generar, pide confirmación y nunca paga dos veces
  la misma escena. Tiene un modo simulado gratis para revisar el video antes de pagar.
- El modo api corre en la nube (Claude Code web/app) sin tu PC; el modo navegador corre en el PC con tu Chrome.

La v1 (skill `cosas-que-pasan`, con Google Flow) no cambia: sigue en tu PC y este skill no la toca.

### Uso rápido

Pídele a Claude: *"haz un cosas que pasan 2 sobre …"*. O a mano:

```bash
pip install -r .claude/skills/cosas-que-pasan-2/requirements.txt
CQP=.claude/skills/cosas-que-pasan-2/cqp.py
python $CQP nuevo "Mi video"                                  # crea proyectos/mi-video/guion.json
python $CQP todo proyectos/mi-video/guion.json --simulado --borrador   # vista previa gratis
# sin clave (PC con tu sesión de Google): Claude repite siguiente → Gemini → recoger y luego
python $CQP render proyectos/mi-video/guion.json --navegador
# con clave de la API de Gemini
python $CQP estimar proyectos/mi-video/guion.json             # cuánto costaría
python $CQP todo proyectos/mi-video/guion.json --confirmar    # genera y arma todo
```

Configurar la clave de Gemini: [referencia/configurar-gemini.md](.claude/skills/cosas-que-pasan-2/referencia/configurar-gemini.md) ·
Formato del guion: [referencia/formato-guion.md](.claude/skills/cosas-que-pasan-2/referencia/formato-guion.md)

### Pruebas

```bash
python -m unittest discover -s tests -v
```
