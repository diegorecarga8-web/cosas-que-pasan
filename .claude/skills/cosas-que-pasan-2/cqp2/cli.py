"""Línea de comandos de Cosas que pasan 2.

  python cqp.py nuevo "Título del video" [--formato vertical]
  python cqp.py validar  proyectos/<slug>/guion.json
  python cqp.py estimar  proyectos/<slug>/guion.json
  python cqp.py generar  proyectos/<slug>/guion.json --confirmar
  python cqp.py render   proyectos/<slug>/guion.json [--borrador]
  python cqp.py todo     proyectos/<slug>/guion.json --confirmar
  python cqp.py prompts  proyectos/<slug>/guion.json   (hoja para el modo app)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__, medios, precios
from .guion import FORMATOS, ErrorGuion, cargar, estimar_narracion, slugificar
from .recursos import ErrorRecursos, FaltaConfirmar, Modos, Recursos

PLANTILLA = Path(__file__).resolve().parent.parent / "plantillas" / "guion_ejemplo.json"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _cargar_env(ruta: Path) -> None:
    """Lee GEMINI_API_KEY (u otras variables) de un .env local sin pisar las que ya existen."""
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave = clave.strip().removeprefix("export ").strip()
        os.environ.setdefault(clave, valor.strip().strip("'\""))


def _modos(args) -> Modos:
    if getattr(args, "simulado", False):
        return Modos.simulado()
    return Modos(videos=args.videos, imagenes=args.imagenes, voz=args.voz)


def _agregar_modos(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("de dónde salen los recursos")
    g.add_argument("--videos", choices=("api", "app", "simulado"), default="api",
                   help="api: Veo por la API de Gemini · app: clips que dejas en clips/ · simulado: marcadores gratis")
    g.add_argument("--imagenes", choices=("api", "app", "simulado"), default="api")
    g.add_argument("--voz", choices=("api", "simulado", "no"), default="api")
    g.add_argument("--simulado", action="store_true", help="todo simulado: vista previa gratis sin API")


def cmd_nuevo(args) -> int:
    slug = slugificar(args.titulo)
    destino = Path(args.carpeta) / slug / "guion.json"
    if destino.exists():
        print(f"Ya existe {destino}; no lo sobrescribo.")
        return 1
    datos = json.loads(PLANTILLA.read_text(encoding="utf-8"))
    datos["titulo"] = args.titulo
    datos["formato"] = args.formato
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Creado {destino} (a partir de la plantilla de ejemplo: reemplaza las escenas).")
    return 0


def cmd_validar(args) -> int:
    g = cargar(args.guion)
    ancho, alto = g.tamano
    total = 0.0
    filas = []
    for e in g.escenas:
        narr = estimar_narracion(e.narracion)
        dur = max(narr + 0.5, 2.0) if (e.tipo == "video" and narr and not e.mantener_clip) else e.duracion
        total += dur
        extras = [x for x, activo in (("texto", e.texto), ("dato", e.dato), ("sacudida", e.sacudida),
                                      (f"desde {e.imagen_inicial}", e.imagen_inicial), ("refs", e.referencias)) if activo]
        detalle = f"clip {e.duracion:.0f} s" if e.tipo == "video" else f"{e.efecto}"
        filas.append(f"  {e.id:<6} {e.tipo:<7} {detalle:<12} voz ~{narr:>4.1f} s   en video ~{dur:>4.1f} s  {' · '.join(extras)}")
    if g.cierre:
        total += g.duracion_cierre
    print(f"✓ Guion válido: «{g.titulo}» — {g.formato} {ancho}x{alto}, {len(g.escenas)} escenas, "
          f"~{total:.0f} s estimados (la duración real sale de la voz generada)")
    print("\n".join(filas))
    if g.shorts:
        for i, s in enumerate(g.shorts, 1):
            print(f"  short-{i}: «{s.titulo}» con {', '.join(s.escenas)} ({s.encuadre})")
    if g.advertencias:
        print("Avisos:")
        for a in g.advertencias:
            print(f"  - {a}")
    return 0


def cmd_estimar(args) -> int:
    g = cargar(args.guion)
    r = Recursos(g, _modos(args))
    partidas = r.estimar(set(args.rehacer.split(",")) if getattr(args, "rehacer", "") else None)
    print(precios.tabla(partidas))
    videos = [e for e in g.escenas if e.tipo == "video"]
    completo = sum(precios.precio_video(r.precios, g.modelo_video, g.resolucion, e.duracion) for e in videos)
    print(f"  (Referencia: todos los clips de video de este guion con {g.modelo_video} a {g.resolucion} "
          f"costarían ~${completo:.2f})")
    faltan = r.faltantes_app()
    if faltan:
        print("Modo app — archivos que faltan:\n  " + "\n  ".join(faltan))
    return 0


def cmd_prompts(args) -> int:
    from .entrega import hoja_prompts

    g = cargar(args.guion)
    ruta = hoja_prompts(g, Recursos(g, _modos(args)), _dir_entrega(g))
    print(f"Hoja de prompts para la app de Gemini: {ruta}")
    return 0


def _dir_entrega(g) -> Path:
    d = g.dir / "entrega"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_generar(args) -> int:
    g = cargar(args.guion)
    for a in g.advertencias:
        _log(f"aviso: {a}")
    r = Recursos(g, _modos(args))
    rehacer = {x.strip() for x in args.rehacer.split(",") if x.strip()} if args.rehacer else set()
    desconocidas = rehacer - {e.id for e in g.escenas}
    if desconocidas:
        raise ErrorGuion(f"--rehacer con escenas que no existen: {sorted(desconocidas)}")
    faltan = r.generar(rehacer=rehacer, confirmar=args.confirmar, max_usd=args.max_usd, paralelo=args.paralelo, log=_log)
    if faltan:
        from .entrega import hoja_prompts

        _log(f"Hoja con los prompts: {hoja_prompts(g, r, _dir_entrega(g))}")
        return 4
    _log("Recursos listos.")
    return 0


def cmd_render(args) -> int:
    from .entrega import metadata
    from .render import Montaje

    g = cargar(args.guion)
    r = Recursos(g, _modos(args))
    m = Montaje(g, r, borrador=args.borrador, log=_log)
    salidas = [m.principal()]
    if not args.sin_shorts:
        salidas += m.shorts()
    if not args.sin_miniatura:
        salidas.append(m.miniatura())
    salidas.append(metadata(g, m.tramos(), m.dir_entrega))
    print("\nEntrega:")
    for s in salidas:
        extra = f"{medios.duracion(s):.1f} s · " if s.suffix == ".mp4" else ""
        print(f"  {s}  ({extra}{s.stat().st_size / 1e6:.1f} MB)")
    return 0


def cmd_todo(args) -> int:
    codigo = cmd_generar(args)
    return codigo if codigo else cmd_render(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cqp", description=f"Cosas que pasan 2 (v{__version__}): videos con la API de Gemini")
    sub = p.add_subparsers(dest="comando", required=True)

    sp = sub.add_parser("nuevo", help="crea proyectos/<slug>/guion.json desde la plantilla")
    sp.add_argument("titulo")
    sp.add_argument("--formato", choices=list(FORMATOS), default="horizontal")
    sp.add_argument("--carpeta", default="proyectos")
    sp.set_defaults(func=cmd_nuevo)

    sp = sub.add_parser("validar", help="revisa el guion y muestra la línea de tiempo estimada")
    sp.add_argument("guion")
    sp.set_defaults(func=cmd_validar)

    sp = sub.add_parser("estimar", help="costo de lo que falta generar con la API")
    sp.add_argument("guion")
    sp.add_argument("--rehacer", default="")
    _agregar_modos(sp)
    sp.set_defaults(func=cmd_estimar)

    sp = sub.add_parser("prompts", help="hoja de prompts para generar los clips en la app de Gemini")
    sp.add_argument("guion")
    _agregar_modos(sp)
    sp.set_defaults(func=cmd_prompts)

    for nombre, ayuda, func in (("generar", "genera videos, imágenes y voz que falten", cmd_generar),
                                ("render", "arma el video principal, shorts, miniatura y metadata", cmd_render),
                                ("todo", "generar + render", cmd_todo)):
        sp = sub.add_parser(nombre, help=ayuda)
        sp.add_argument("guion")
        _agregar_modos(sp)
        if nombre in ("generar", "todo"):
            sp.add_argument("--confirmar", action="store_true", help="acepta el costo estimado de la API")
            sp.add_argument("--max-usd", type=float, default=None, help="no generar si el costo estimado supera este tope")
            sp.add_argument("--rehacer", default="", help="ids de escenas a regenerar, separados por comas")
            sp.add_argument("--paralelo", type=int, default=2, help="clips de Veo generándose a la vez")
        if nombre in ("render", "todo"):
            sp.add_argument("--borrador", action="store_true", help="render rápido a media resolución")
            sp.add_argument("--sin-shorts", action="store_true")
            sp.add_argument("--sin-miniatura", action="store_true")
        sp.set_defaults(func=func)

    args = p.parse_args(argv)
    _cargar_env(Path.cwd() / ".env")
    try:
        return args.func(args)
    except FaltaConfirmar as e:
        print(str(e))
        return 3
    except (ErrorGuion, ErrorRecursos, medios.ErrorMedios) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:  # ErrorRender, ErrorGemini
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
