"""Archivos de entrega que no son video: metadata para YouTube y hoja de prompts del modo app."""

from __future__ import annotations

import json
from pathlib import Path

from .guion import Guion
from .recursos import Recursos


def _marca(t: float) -> str:
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def metadata(g: Guion, tramos, dir_entrega: Path) -> Path:
    lineas = [f"TÍTULO: {g.titulo}", "", "DESCRIPCIÓN:",
              g.descripcion or "(agrega 'metadata.descripcion' en el guion)", ""]
    capitulos = [(tr.inicio, tr.escena.capitulo) for tr in tramos if tr.escena.capitulo]
    if capitulos:
        if capitulos[0][0] > 0:
            capitulos.insert(0, (0.0, "Intro"))
        fin = tramos[-1].inicio + tramos[-1].duracion if tramos else 0.0
        limites = [t for t, _ in capitulos[1:]] + [fin]
        cortos = [c for (t, c), hasta in zip(capitulos, limites) if hasta - t < 10]
        lineas += ["CAPÍTULOS (pégalos en la descripción):", *[f"{_marca(t)} {c}" for t, c in capitulos]]
        if len(capitulos) < 3 or cortos:
            lineas.append("(Ojo: YouTube solo los activa con 3 o más capítulos de al menos 10 s cada uno"
                          + (f"; muy cortos: {', '.join(cortos)}" if cortos else "") + ")")
        lineas.append("")
    if g.etiquetas:
        lineas += ["ETIQUETAS:", ", ".join(g.etiquetas), ""]
    if g.shorts:
        lineas.append("SHORTS:")
        lineas += [f"  short-{i}.mp4 — {s.titulo}" for i, s in enumerate(g.shorts, 1)]
        lineas.append("")
    manifest = g.dir / "manifest.json"
    if manifest.exists():
        total = json.loads(manifest.read_text(encoding="utf-8")).get("usd_estimado_total", 0)
        lineas.append(f"Costo estimado acumulado en la API de Gemini para este proyecto: ${total:.2f} USD")
    ruta = dir_entrega / "metadata.txt"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def prompt_app(g: Guion, e) -> str:
    formato = "Vertical 9:16 video." if g.formato == "vertical" else "Horizontal 16:9 video."
    if e.tipo == "imagen":
        formato = "Vertical 9:16 image." if g.formato == "vertical" else "Horizontal 16:9 image."
    return f"{g.prompt_visual(e)} {formato} Avoid: {g.evitar}."


def hoja_prompts(g: Guion, r: Recursos, dir_entrega: Path) -> Path:
    videos = [e for e in g.escenas if e.tipo == "video"]
    imagenes = [e for e in g.escenas if e.tipo == "imagen"]
    md = [
        f"# Prompts para la app de Gemini — {g.titulo}",
        "",
        "Modo app: generas cada clip en la app de Gemini con tu plan Google AI Pro (usa la cuota del plan, "
        "no la API) y guardas el archivo con el nombre indicado dentro de la carpeta del proyecto:",
        f"`{g.dir.name}/clips/` para videos y `{g.dir.name}/imagenes/` para imágenes.",
        "",
        "1. Abre gemini.google.com (o la app), elige la herramienta de **Video**, pega el prompt y espera el clip.",
        "2. Descárgalo y renómbralo exactamente como se indica (por ejemplo `e01.mp4`).",
        "3. Súbelo a la carpeta del proyecto: desde el PC, o desde el celular con la web/app de GitHub "
        "(Add file → Upload files) en la rama del proyecto.",
        "4. Cuando estén todos, pide a Claude que renderice con `--videos app`.",
        "",
        "Los clips de la app suelen durar 8 s: el montaje los recorta al largo de la narración. Si la app "
        "entrega otra proporción, el montaje la recorta para llenar el cuadro.",
        "",
    ]
    for e in videos:
        estado = "✅ ya está" if r.modos.videos == "app" and r.video(e) else "pendiente"
        md += [f"## {e.id} → `clips/{e.id}.mp4` ({estado})", "", "```text", prompt_app(g, e), "```", ""]
    if imagenes:
        md += ["## Imágenes (solo si también las haces en la app: `--imagenes app`)", ""]
        for e in imagenes:
            md += [f"### {e.id} → `imagenes/{e.id}.png`", "", "```text", prompt_app(g, e), "```", ""]
    ruta = dir_entrega / "PROMPTS_GEMINI_APP.md"
    ruta.write_text("\n".join(md), encoding="utf-8")
    return ruta
