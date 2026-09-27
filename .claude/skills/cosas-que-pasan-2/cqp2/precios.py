"""Precios aproximados de la API de Gemini (USD) para estimar el costo antes de generar.

Son referencias de septiembre de 2026: revisa los vigentes en
https://ai.google.dev/gemini-api/docs/pricing . Para corregirlos sin tocar el código, crea un
`precios.json` junto al guion con la misma forma que PRECIOS (solo las claves que cambien).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

PRECIOS = {
    # USD por segundo de video generado (Veo siempre incluye audio en la API de Gemini)
    "video_por_segundo": {
        "veo-3.1-lite-generate-preview": {"720p": 0.05, "1080p": 0.08},
        "veo-3.1-fast-generate-preview": {"720p": 0.10, "1080p": 0.12, "4k": 0.30},
        "veo-3.1-generate-preview": {"720p": 0.40, "1080p": 0.40, "4k": 0.60},
    },
    # USD por imagen (~1K)
    "imagen": {
        "gemini-3.1-flash-image": 0.067,
        "gemini-3-pro-image": 0.134,
        "gemini-2.5-flash-image": 0.039,
    },
    # USD por minuto de voz generada (salida de audio de los modelos TTS)
    "voz_por_minuto": 0.03,
    # Si el modelo no está en la tabla se usa el precio alto para no quedarse corto
    "video_desconocido_por_segundo": 0.40,
    "imagen_desconocida": 0.15,
}


def cargar_precios(dir_proyecto: Path | None = None) -> dict:
    precios = copy.deepcopy(PRECIOS)
    if dir_proyecto and (dir_proyecto / "precios.json").exists():
        extra = json.loads((dir_proyecto / "precios.json").read_text(encoding="utf-8"))
        for clave, valor in extra.items():
            if isinstance(valor, dict) and isinstance(precios.get(clave), dict):
                precios[clave].update(valor)
            else:
                precios[clave] = valor
    return precios


@dataclass
class Partida:
    escena: str
    tipo: str  # video | imagen | voz
    modelo: str
    detalle: str
    usd: float


def precio_video(precios: dict, modelo: str, resolucion: str, segundos: float) -> float:
    tabla = precios["video_por_segundo"].get(modelo, {})
    por_segundo = tabla.get(resolucion, precios["video_desconocido_por_segundo"])
    return por_segundo * segundos


def precio_imagen(precios: dict, modelo: str) -> float:
    return precios["imagen"].get(modelo, precios["imagen_desconocida"])


def precio_voz(precios: dict, segundos: float) -> float:
    return precios["voz_por_minuto"] * segundos / 60


def total(partidas: list[Partida]) -> float:
    return round(sum(p.usd for p in partidas), 2)


def tabla(partidas: list[Partida]) -> str:
    if not partidas:
        return "Nada que generar con la API (todo está en caché o se usa modo app/simulado): costo $0.00"
    filas = [f"  {p.escena:<8} {p.tipo:<7} {p.modelo:<32} {p.detalle:<22} ${p.usd:,.3f}" for p in partidas]
    por_tipo = {}
    for p in partidas:
        por_tipo[p.tipo] = por_tipo.get(p.tipo, 0) + p.usd
    resumen = " · ".join(f"{t}: ${v:,.2f}" for t, v in por_tipo.items())
    return "\n".join([
        f"  {'escena':<8} {'tipo':<7} {'modelo':<32} {'detalle':<22} costo",
        *filas,
        f"  TOTAL ESTIMADO: ${total(partidas):,.2f} USD  ({resumen})  — precios aproximados, ver precios.py",
    ])
