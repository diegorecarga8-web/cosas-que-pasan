"""Recursos de cada escena (video, imagen y voz): dónde viven, cuánto cuestan y cómo se generan.

Modos por tipo de recurso:
  api       -> API de Gemini (Veo / imagen / voz). Automático, se paga por uso.
  app       -> archivos que tú generas en la app de Gemini (plan Google AI Pro) y dejas en clips/ o imagenes/.
  simulado  -> marcadores gratis generados con ffmpeg, para revisar ritmo, textos y efectos antes de pagar.
  no        -> (solo voz) sin narración generada.

Todo lo generado por la API queda en caché con un nombre que depende del prompt y los parámetros:
si vuelves a ejecutar, solo se genera lo que falta o lo que cambió. Nunca se paga dos veces lo mismo.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import medios, precios
from .guion import Escena, Guion, estimar_narracion
from .subtitulos import Documento, sin_marcas

MODOS_VIDEO = ("api", "app", "simulado")
MODOS_IMAGEN = ("api", "app", "simulado")
MODOS_VOZ = ("api", "simulado", "no")
EXT_VIDEO = (".mp4", ".mov", ".webm", ".mkv")
EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")
EXT_VOZ = (".wav", ".mp3", ".m4a", ".ogg")
RESOLUCION_SIMULADA = {"16:9": (1280, 720), "9:16": (720, 1280)}


class ErrorRecursos(RuntimeError):
    pass


class FaltaConfirmar(ErrorRecursos):
    """El costo estimado es mayor que cero y no se pasó --confirmar."""


@dataclass
class Modos:
    videos: str = "api"
    imagenes: str = "api"
    voz: str = "api"

    @classmethod
    def simulado(cls) -> "Modos":
        return cls("simulado", "simulado", "simulado")


def _huella(datos: dict) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def _huella_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:10]


def hay_clave_api() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


class Recursos:
    def __init__(self, guion: Guion, modos: Modos):
        for valor, validos, nombre in ((modos.videos, MODOS_VIDEO, "videos"), (modos.imagenes, MODOS_IMAGEN, "imagenes"),
                                       (modos.voz, MODOS_VOZ, "voz")):
            if valor not in validos:
                raise ErrorRecursos(f"Modo de {nombre} inválido: {valor} (usa {', '.join(validos)})")
        self.g = guion
        self.modos = modos
        self.dir = guion.dir
        self.precios = precios.cargar_precios(self.dir)
        self._lock = threading.Lock()
        self._gemini = None

    # ------------------------------------------------------------------ claves de caché

    def _huella_imagen_inicial(self, e: Escena) -> str:
        if not e.imagen_inicial:
            return ""
        if e.imagen_inicial.startswith("@"):
            fuente = self.g.escena(e.imagen_inicial[1:])
            if self.modos.imagenes == "app":
                ruta = self.imagen(fuente)
                return _huella_archivo(ruta) if ruta else f"pendiente:{fuente.id}"
            return self.clave_imagen(fuente)
        return _huella_archivo(self.dir / e.imagen_inicial)

    def clave_video(self, e: Escena) -> str:
        return _huella({
            "modelo": self.g.modelo_video, "prompt": self.g.prompt_visual(e), "evitar": self.g.evitar,
            "aspecto": self.g.aspecto, "resolucion": self.g.resolucion, "duracion": int(e.duracion),
            "inicial": self._huella_imagen_inicial(e),
            "referencias": [_huella_archivo(self.dir / r) for r in e.referencias],
        })

    def clave_imagen(self, e: Escena) -> str:
        return _huella({"modelo": self.g.modelo_imagen, "prompt": self.g.prompt_visual(e), "aspecto": self.g.aspecto})

    def clave_voz(self, e: Escena) -> str:
        return _huella({"modelo": self.g.modelo_voz, "voz": self.g.voz, "indicaciones": self.g.indicaciones_voz,
                        "texto": sin_marcas(e.narracion)})

    # ------------------------------------------------------------------ ubicación

    @staticmethod
    def _buscar(carpeta: Path, base: str, extensiones: tuple[str, ...]) -> Path | None:
        for ext in extensiones:
            ruta = carpeta / f"{base}{ext}"
            if ruta.exists() and ruta.stat().st_size > 0:
                return ruta
        return None

    def _carpeta(self, modo: str, tipo: str) -> Path:
        return self.dir / "assets" / ("simulado" if modo == "simulado" else "") / tipo

    def video(self, e: Escena) -> Path | None:
        if self.modos.videos == "app":
            return self._buscar(self.dir / "clips", e.id, EXT_VIDEO)
        return self._buscar(self._carpeta(self.modos.videos, "videos"), f"{e.id}-{self.clave_video(e)}", EXT_VIDEO)

    def imagen(self, e: Escena) -> Path | None:
        if self.modos.imagenes == "app":
            return self._buscar(self.dir / "imagenes", e.id, EXT_IMAGEN)
        return self._buscar(self._carpeta(self.modos.imagenes, "imagenes"), f"{e.id}-{self.clave_imagen(e)}", EXT_IMAGEN)

    def voz(self, e: Escena) -> Path | None:
        if not e.narracion or not self.g.voz_activa:
            return None
        propia = self._buscar(self.dir / "voz", e.id, EXT_VOZ)  # tu propia grabación siempre tiene prioridad
        if propia or self.modos.voz == "no":
            return propia
        return self._buscar(self._carpeta(self.modos.voz, "voz"), f"{e.id}-{self.clave_voz(e)}", (".wav",))

    def fuente_visual(self, e: Escena) -> Path | None:
        return self.video(e) if e.tipo == "video" else self.imagen(e)

    # ------------------------------------------------------------------ pendientes y costo

    def pendientes(self, rehacer: set[str] | None = None) -> list[tuple[str, Escena]]:
        rehacer = rehacer or set()
        lista = []
        for e in self.g.escenas:
            if e.tipo == "imagen" and (e.id in rehacer or not self.imagen(e)):
                lista.append(("imagen", e))
        for e in self.g.escenas:
            if e.narracion and self.g.voz_activa and self.modos.voz != "no" and (e.id in rehacer or not self.voz(e)):
                if not self._buscar(self.dir / "voz", e.id, EXT_VOZ):
                    lista.append(("voz", e))
        for e in self.g.escenas:
            if e.tipo == "video" and (e.id in rehacer or not self.video(e)):
                lista.append(("video", e))
        return lista

    def _modo(self, tipo: str) -> str:
        return {"video": self.modos.videos, "imagen": self.modos.imagenes, "voz": self.modos.voz}[tipo]

    def estimar(self, rehacer: set[str] | None = None) -> list[precios.Partida]:
        partidas = []
        for tipo, e in self.pendientes(rehacer):
            if self._modo(tipo) != "api":
                continue
            if tipo == "video":
                usd = precios.precio_video(self.precios, self.g.modelo_video, self.g.resolucion, e.duracion)
                partidas.append(precios.Partida(e.id, "video", self.g.modelo_video,
                                                f"{e.duracion:.0f} s · {self.g.resolucion} · {self.g.aspecto}", usd))
            elif tipo == "imagen":
                partidas.append(precios.Partida(e.id, "imagen", self.g.modelo_imagen, self.g.aspecto,
                                                precios.precio_imagen(self.precios, self.g.modelo_imagen)))
            else:
                seg = estimar_narracion(e.narracion)
                partidas.append(precios.Partida(e.id, "voz", self.g.modelo_voz, f"~{seg:.0f} s · {self.g.voz}",
                                                precios.precio_voz(self.precios, seg)))
        return partidas

    def faltantes_app(self) -> list[str]:
        """Archivos que tienes que dejar tú (modo app) y todavía no están."""
        faltan = []
        for e in self.g.escenas:
            if e.tipo == "video" and self.modos.videos == "app" and not self.video(e):
                faltan.append(f"clips/{e.id}.mp4")
            if e.tipo == "imagen" and self.modos.imagenes == "app" and not self.imagen(e):
                faltan.append(f"imagenes/{e.id}.png")
        return faltan

    # ------------------------------------------------------------------ generación

    def generar(self, rehacer: set[str] | None = None, confirmar: bool = False, max_usd: float | None = None,
                paralelo: int = 2, log=print) -> list[str]:
        rehacer = rehacer or set()
        partidas = self.estimar(rehacer)
        costo = precios.total(partidas)
        if costo > 0:
            if not hay_clave_api():
                raise ErrorRecursos(
                    "Falta la clave de la API de Gemini (variable GEMINI_API_KEY). Mira referencia/configurar-gemini.md,\n"
                    "o usa --videos app (clips hechos en la app de Gemini) o --simulado para una vista previa gratis.")
            if max_usd is not None and costo > max_usd:
                raise ErrorRecursos(f"El costo estimado (${costo:.2f}) supera el tope --max-usd {max_usd:.2f}.\n"
                                    + precios.tabla(partidas))
            if not confirmar:
                raise FaltaConfirmar(precios.tabla(partidas) + "\n\nNo se generó nada. Si estás de acuerdo con el "
                                     "costo, vuelve a ejecutar con --confirmar.")
            log(precios.tabla(partidas))

        trabajos = [(t, e) for t, e in self.pendientes(rehacer) if self._modo(t) != "app"]
        errores: list[str] = []
        for tipo in ("imagen", "voz"):  # rápidos y previos a los videos (imagen_inicial)
            for t, e in trabajos:
                if t == tipo:
                    try:
                        self._generar_uno(t, e, log)
                    except Exception as exc:  # seguimos con el resto y resumimos al final
                        errores.append(f"[{e.id}] {t}: {exc}")
                        log(f"[{e.id}] ERROR {t}: {exc}")
        videos = [e for t, e in trabajos if t == "video"]
        if videos:
            with ThreadPoolExecutor(max_workers=max(1, paralelo)) as pool:
                futuros = {pool.submit(self._generar_uno, "video", e, log): e for e in videos}
                for fut in as_completed(futuros):
                    e = futuros[fut]
                    try:
                        fut.result()
                    except Exception as exc:
                        errores.append(f"[{e.id}] video: {exc}")
                        log(f"[{e.id}] ERROR video: {exc}")
        faltan = self.faltantes_app()
        if faltan:
            log("Modo app: faltan estos archivos (genera en la app de Gemini y guárdalos así):\n  " + "\n  ".join(faltan))
        if errores:
            raise ErrorRecursos("Algunos recursos fallaron (lo demás quedó guardado; vuelve a ejecutar para reintentar):\n"
                                + "\n".join(errores))
        return faltan

    def _destino(self, tipo: str, e: Escena, ext: str) -> Path:
        modo = self._modo(tipo)
        carpeta = self._carpeta(modo, {"video": "videos", "imagen": "imagenes", "voz": "voz"}[tipo])
        carpeta.mkdir(parents=True, exist_ok=True)
        clave = {"video": self.clave_video, "imagen": self.clave_imagen, "voz": self.clave_voz}[tipo](e)
        for viejo in carpeta.glob(f"{e.id}-*"):  # versiones anteriores de la escena
            viejo.unlink()
        return carpeta / f"{e.id}-{clave}{ext}"

    def _generar_uno(self, tipo: str, e: Escena, log) -> None:
        modo = self._modo(tipo)
        inicio = time.time()
        if modo == "simulado":
            ruta = self._simular(tipo, e)
            log(f"[{e.id}] {tipo} simulado → {ruta.relative_to(self.dir)}")
            return
        api = self._api()
        if tipo == "video":
            inicial = None
            if e.imagen_inicial:
                inicial = self.imagen(self.g.escena(e.imagen_inicial[1:])) if e.imagen_inicial.startswith("@") \
                    else self.dir / e.imagen_inicial
                if not inicial:
                    raise ErrorRecursos(f"falta la imagen inicial {e.imagen_inicial}")
            log(f"[{e.id}] video: enviando a {self.g.modelo_video} ({e.duracion:.0f} s, {self.g.resolucion}, {self.g.aspecto})…")
            tmp = self._destino("video", e, ".mp4.parcial")
            api.video(self.g.prompt_visual(e), tmp, modelo=self.g.modelo_video, aspecto=self.g.aspecto,
                      resolucion=self.g.resolucion, duracion=int(e.duracion), evitar=self.g.evitar,
                      imagen_inicial=inicial, referencias=[self.dir / r for r in e.referencias])
            ruta = tmp.with_name(tmp.name.replace(".parcial", ""))
            os.replace(tmp, ruta)
            usd = precios.precio_video(self.precios, self.g.modelo_video, self.g.resolucion, e.duracion)
            modelo = self.g.modelo_video
        elif tipo == "imagen":
            datos, mime = api.imagen(self.g.prompt_visual(e), modelo=self.g.modelo_imagen, aspecto=self.g.aspecto)
            ext = {"image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".png")
            ruta = self._destino("imagen", e, ext)
            ruta.write_bytes(datos)
            usd = precios.precio_imagen(self.precios, self.g.modelo_imagen)
            modelo = self.g.modelo_imagen
        else:
            ruta = self._destino("voz", e, ".wav")
            api.voz(sin_marcas(e.narracion), ruta, modelo=self.g.modelo_voz, voz=self.g.voz,
                    indicaciones=self.g.indicaciones_voz)
            usd = precios.precio_voz(self.precios, medios.duracion(ruta))
            modelo = self.g.modelo_voz
        log(f"[{e.id}] {tipo} listo en {time.time() - inicio:.0f} s → {ruta.relative_to(self.dir)} (~${usd:.3f})")
        self._anotar(e.id, tipo, ruta, modelo, usd)

    def _anotar(self, escena: str, tipo: str, ruta: Path, modelo: str, usd: float) -> None:
        with self._lock:
            archivo = self.dir / "manifest.json"
            registro = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {"generados": []}
            registro["generados"].append({
                "escena": escena, "tipo": tipo, "archivo": str(ruta.relative_to(self.dir)).replace("\\", "/"),
                "modelo": modelo, "usd_estimado": round(usd, 4),
                "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            registro["usd_estimado_total"] = round(sum(x["usd_estimado"] for x in registro["generados"]), 2)
            archivo.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")

    def _api(self):
        if self._gemini is None:
            if not hay_clave_api():
                raise ErrorRecursos("Falta GEMINI_API_KEY (ver referencia/configurar-gemini.md)")
            from .gemini import Gemini

            self._gemini = Gemini()
        return self._gemini

    # ------------------------------------------------------------------ simulados (gratis)

    def _simular(self, tipo: str, e: Escena) -> Path:
        ancho, alto = RESOLUCION_SIMULADA[self.g.aspecto]
        indice = self.g.escenas.index(e)
        tonos = ["0x1d3557", "0x6a040f", "0x2d6a4f", "0x5a189a", "0x9c6644", "0x006d77", "0x3a0ca3", "0x7f5539"]
        c0, c1 = tonos[indice % len(tonos)], tonos[(indice + 3) % len(tonos)]
        if tipo == "voz":
            ruta = self._destino("voz", e, ".wav")
            seg = max(0.8, estimar_narracion(e.narracion) - 0.3)
            medios.ejecutar(["-f", "lavfi", "-i", f"sine=frequency=180:sample_rate=24000:duration={seg:.2f}",
                             "-af", "volume=0.06", "-ac", "1", str(ruta)], descripcion="voz simulada")
            return ruta
        carpeta = self.dir / "render" / "simulado"
        carpeta.mkdir(parents=True, exist_ok=True)
        fontsdir = medios.preparar_fuentes(carpeta)
        doc = Documento(ancho, alto)
        doc.placa(f"SIMULADO · {e.id} · {tipo}\n{e.prompt[:220]}")
        doc.guardar(carpeta / f"{e.id}.ass")
        filtro = f"ass={e.id}.ass:fontsdir={fontsdir}"
        if tipo == "imagen":
            ruta = self._destino("imagen", e, ".png")
            medios.ejecutar(["-f", "lavfi", "-i", f"gradients=s={ancho}x{alto}:c0={c0}:c1={c1}:x0=0:y0=0:x1={ancho}:y1={alto}:d=1",
                             "-vf", filtro, "-frames:v", "1", str(ruta.resolve())], cwd=carpeta, descripcion="imagen simulada")
            return ruta
        ruta = self._destino("video", e, ".mp4")
        medios.ejecutar([
            "-f", "lavfi", "-i", f"gradients=s={ancho}x{alto}:c0={c0}:c1={c1}:speed=0.03:d={e.duracion}:r=24",
            "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.03:sample_rate=48000:duration={e.duracion}",
            "-vf", filtro, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(ruta.resolve()),
        ], cwd=carpeta, descripcion="video simulado")
        return ruta


def escribir_wav(ruta: Path, pcm: bytes, frecuencia: int = 24000, canales: int = 1, bytes_muestra: int = 2) -> None:
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(canales)
        w.setsampwidth(bytes_muestra)
        w.setframerate(frecuencia)
        w.writeframes(pcm)
