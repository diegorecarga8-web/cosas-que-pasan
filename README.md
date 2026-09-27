# Cosas que pasan

## Cosas que pasan 2 (Gemini / Veo)

Skill aparte en [`.claude/skills/cosas-que-pasan-2/`](.claude/skills/cosas-que-pasan-2/SKILL.md). Genera
el video principal, los shorts, la miniatura y la metadata de YouTube:

- **Clips de video** con Veo 3.1, **imágenes** con Nano Banana y **narración** con Gemini TTS, todo por la
  API de Gemini (o con clips hechos a mano en la app de Gemini, modo app).
- **Montaje** con ffmpeg: gancho animado, sacudida de cámara, zoom/paneo en imágenes, tarjetas de datos,
  subtítulos con palabras resaltadas, música que baja sola bajo la voz, cierre y volumen normalizado.
- **Caché y control de gasto:** estima el costo antes de generar, pide confirmación y nunca paga dos veces
  la misma escena. Tiene un modo simulado gratis para revisar el video antes de pagar.
- Corre en la nube (Claude Code web/app) o en el PC, sin depender del navegador.

La v1 (skill `cosas-que-pasan`, con Google Flow) no cambia: sigue en tu PC y este skill no la toca.

### Uso rápido

Pídele a Claude: *"haz un cosas que pasan 2 sobre …"*. O a mano:

```bash
pip install -r .claude/skills/cosas-que-pasan-2/requirements.txt
CQP=.claude/skills/cosas-que-pasan-2/cqp.py
python $CQP nuevo "Mi video"                                  # crea proyectos/mi-video/guion.json
python $CQP todo proyectos/mi-video/guion.json --simulado --borrador   # vista previa gratis
python $CQP estimar proyectos/mi-video/guion.json             # cuánto costaría
python $CQP todo proyectos/mi-video/guion.json --confirmar    # genera y arma todo
```

Configurar la clave de Gemini: [referencia/configurar-gemini.md](.claude/skills/cosas-que-pasan-2/referencia/configurar-gemini.md) ·
Formato del guion: [referencia/formato-guion.md](.claude/skills/cosas-que-pasan-2/referencia/formato-guion.md)

### Pruebas

```bash
python -m unittest discover -s tests -v
```
