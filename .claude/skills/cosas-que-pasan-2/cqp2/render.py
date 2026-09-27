"""Montaje con ffmpeg: escenas -> video principal, shorts y miniatura.

1. Cada escena se renderiza como un segmento (encuadre, zoom/paneo, sacudida, voz + audio del clip).
   Los segmentos quedan en caché en render/segmentos: si solo cambian los textos, no se rehacen.
2. Un paso final une los segmentos, dibuja los textos (subtítulos ASS), mezcla la música con
   "ducking" bajo la voz y normaliza el volumen a -14 LUFS (lo que usa YouTube).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import medios
from .guion import Escena, Guion
from .recursos import Recursos
from .subtitulos import Documento

FPS = 30
VERSION_SEGMENTOS = 2  # súbela si cambia cómo se renderiza un segmento, para invalidar la caché
MINIATURA = {"horizontal": (1280, 720), "vertical": (1080, 1920)}


class ErrorRender(RuntimeError):
    pass


@dataclass
class Tramo:
    escena: Escena
    fuente: Path
    voz: Path | None
    dur_voz: float
    duracion: float
    sacudida: bool
    inicio: float = 0.0


def _par(n: float) -> int:
    return max(2, int(round(n / 2)) * 2)


def _huella(*partes) -> str:
    return hashlib.sha256(json.dumps(partes, default=str).encode()).hexdigest()[:10]


def _firma_archivo(ruta: Path | None) -> str:
    if not ruta:
        return ""
    st = ruta.stat()
    return f"{ruta.name}:{st.st_size}:{int(st.st_mtime)}"


class Montaje:
    def __init__(self, guion: Guion, recursos: Recursos, borrador: bool = False, log=print):
        self.g = guion
        self.r = recursos
        self.borrador = borrador
        self.log = log
        self.dir_render = guion.dir / "render"
        self.dir_segmentos = self.dir_render / "segmentos"
        self.dir_entrega = guion.dir / "entrega"
        for d in (self.dir_segmentos, self.dir_entrega):
            d.mkdir(parents=True, exist_ok=True)
        self.fontsdir = medios.preparar_fuentes(self.dir_render)
        self.preset, self.crf = ("ultrafast", "30") if borrador else ("veryfast", "18")
        self.sufijo = "-borrador" if borrador else ""

    # ------------------------------------------------------------------ línea de tiempo

    def tramos(self, ids: list[str] | None = None, gancho: bool = False) -> list[Tramo]:
        escenas = [self.g.escena(i) for i in ids] if ids else list(self.g.escenas)
        faltan = [f"{e.id} ({e.tipo})" for e in escenas if not self.r.fuente_visual(e)]
        if faltan:
            raise ErrorRender("Faltan recursos visuales para: " + ", ".join(faltan) +
                              "\nEjecuta 'generar' (o deja los archivos del modo app) antes de renderizar.")
        tramos, t = [], 0.0
        for i, e in enumerate(escenas):
            fuente = self.r.fuente_visual(e)
            voz = self.r.voz(e)
            dur_voz = medios.duracion(voz) if voz else 0.0
            sacudida = e.sacudida if ids is None else (e.sacudida or (i == 0 and gancho))
            dur = round(self._duracion(e, fuente, dur_voz) * FPS) / FPS
            tramos.append(Tramo(e, fuente, voz, dur_voz, dur, sacudida, inicio=t))
            t += dur
        return tramos

    @staticmethod
    def _duracion(e: Escena, fuente: Path, dur_voz: float) -> float:
        necesaria = dur_voz + 0.5 if dur_voz else 0.0  # 0.15 s de entrada + 0.35 s de respiro
        if e.tipo == "video":
            clip = medios.duracion(fuente)
            if not dur_voz:
                return clip
            return max(clip, necesaria) if e.mantener_clip else max(necesaria, 2.0)
        if e.duracion_fija:
            return max(e.duracion, necesaria)
        return max(dur_voz + 0.6, 2.0) if dur_voz else e.duracion

    # ------------------------------------------------------------------ segmentos

    def _cadena_video(self, tr: Tramo, W: int, H: int, encuadre: str, entrada: str) -> str:
        e = tr.escena
        pasos = []
        if e.tipo == "video":
            base = f"[{entrada}]setpts=PTS-STARTPTS,fps={FPS}"
            if encuadre == "relleno" and self._aspecto_distinto(tr.fuente, W, H):
                pasos.append(f"{base},split=2[b0][f0]")
                pasos.append(self._fondo_borroso("b0", W, H))
                pasos.append(f"[f0]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg]")
                pasos.append("[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[vb]")
            else:
                pasos.append(f"{base},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1[vb]")
        else:
            n = max(1, round(tr.duracion * FPS))
            if encuadre == "relleno" and self._aspecto_distinto(tr.fuente, W, H):
                wi, hi = medios.dimensiones(tr.fuente)
                wf, hf = (W, _par(W * hi / wi)) if wi / hi > W / H else (_par(H * wi / hi), H)
                pasos.append(f"[{entrada}]split=2[b0][f0]")
                pasos.append(self._fondo_borroso("b0", W, H))
                pasos.append(f"[f0]{self._zoompan(e.efecto, wf, hf, n)}[fg]")
                pasos.append("[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,setsar=1[vb]")
            else:
                pasos.append(f"[{entrada}]{self._zoompan(e.efecto, W, H, n)},setsar=1[vb]")
        ultimo = "vb"
        if tr.sacudida:
            a = 0.02 * min(W, H)
            ws, hs = _par(W * 1.06), _par(H * 1.06)
            pasos.append(f"[{ultimo}]scale={ws}:{hs},crop={W}:{H}:"
                         f"x='(iw-ow)/2+{a:.1f}*exp(-2.2*t)*sin(2*PI*11*t)':"
                         f"y='(ih-oh)/2+{a:.1f}*exp(-2.2*t)*cos(2*PI*13*t)'[vs]")
            ultimo = "vs"
        extension = ""
        if e.tipo == "video":
            # Si la narración es más larga que el clip se congela el último cuadro; el margen extra
            # garantiza que el segmento tenga exactamente tr.duracion y el audio no se desfase al unir.
            falta = max(0.0, tr.duracion - medios.duracion(tr.fuente))
            extension = f"tpad=stop_mode=clone:stop_duration={falta + 0.3:.3f},"
        pasos.append(f"[{ultimo}]{extension}trim=duration={tr.duracion:.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v]")
        return ";".join(pasos)

    def _aspecto_distinto(self, fuente: Path, W: int, H: int) -> bool:
        wi, hi = medios.dimensiones(fuente)
        return abs(wi / hi - W / H) > 0.05

    @staticmethod
    def _fondo_borroso(entrada: str, W: int, H: int) -> str:
        w4, h4 = _par(W / 4), _par(H / 4)
        return (f"[{entrada}]scale={w4}:{h4}:force_original_aspect_ratio=increase,crop={w4}:{h4},"
                f"boxblur=8:2,scale={W}:{H},eq=brightness=-0.07[bg]")

    @staticmethod
    def _zoompan(efecto: str, W: int, H: int, n: int) -> str:
        wz, hz = _par(W * 1.5), _par(H * 1.5)
        centro_x, centro_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
        z, x, y = {
            "zoom_in": (f"1+0.12*on/{n}", centro_x, centro_y),
            "zoom_out": (f"1.12-0.12*on/{n}", centro_x, centro_y),
            "paneo_izq": ("1.12", f"(iw-iw/zoom)*(1-on/{n})", centro_y),
            "paneo_der": ("1.12", f"(iw-iw/zoom)*on/{n}", centro_y),
            "ninguno": ("1", "0", "0"),
        }[efecto]
        return (f"scale={wz}:{hz}:force_original_aspect_ratio=increase,crop={wz}:{hz},"
                f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS}")

    def _segmento(self, tr: Tramo, W: int, H: int, encuadre: str) -> Path:
        e = tr.escena
        volumen = e.volumen_clip if e.volumen_clip is not None else (0.3 if tr.voz else 0.9)
        clave = _huella(VERSION_SEGMENTOS, e.id, e.tipo, e.efecto, _firma_archivo(tr.fuente), _firma_archivo(tr.voz), W, H, encuadre,
                        tr.sacudida, round(tr.duracion, 3), volumen, self.preset, self.crf)
        destino = self.dir_segmentos / f"{e.id}-{clave}.mp4"
        if destino.exists():
            return destino
        args: list[str] = []
        if e.tipo == "video":
            args += ["-i", str(tr.fuente)]
        else:
            args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{tr.duracion:.3f}", "-i", str(tr.fuente)]
        filtros = [self._cadena_video(tr, W, H, encuadre, "0:v")]
        fuentes_audio = []
        siguiente = 1
        if e.tipo == "video" and medios.tiene_audio(tr.fuente):
            filtros.append(f"[0:a]volume={volumen:.2f},aresample=48000,aformat=channel_layouts=stereo[ca]")
            fuentes_audio.append("[ca]")
        if tr.voz:
            args += ["-i", str(tr.voz)]
            filtros.append(f"[{siguiente}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=150:all=1[na]")
            fuentes_audio.append("[na]")
            siguiente += 1
        if not fuentes_audio:
            args += ["-f", "lavfi", "-t", f"{tr.duracion:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            fuentes_audio.append(f"[{siguiente}:a]")
        mezcla = fuentes_audio[0] if len(fuentes_audio) == 1 else \
            f"{''.join(fuentes_audio)}amix=inputs={len(fuentes_audio)}:normalize=0:duration=longest"
        if len(fuentes_audio) == 1:
            filtros.append(f"{mezcla}apad,atrim=duration={tr.duracion:.3f},asetpts=PTS-STARTPTS[a]")
        else:
            filtros.append(f"{mezcla},apad,atrim=duration={tr.duracion:.3f},asetpts=PTS-STARTPTS[a]")
        tmp = destino.with_suffix(".parcial.mp4")
        args += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
                 "-c:v", "libx264", "-preset", self.preset, "-crf", self.crf, "-pix_fmt", "yuv420p", "-r", str(FPS),
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", f"{tr.duracion:.3f}", str(tmp)]
        self.log(f"  segmento {e.id} ({e.tipo}, {tr.duracion:.1f} s)")
        medios.ejecutar(args, descripcion=f"segmento {e.id}")
        tmp.replace(destino)
        return destino

    def _segmento_cierre(self, ultimo: Path, W: int, H: int, duracion: float) -> Path:
        destino = self.dir_segmentos / f"cierre-{_huella(VERSION_SEGMENTOS, ultimo.name, W, H, duracion, self.preset)}.mp4"
        if destino.exists():
            return destino
        cuadro = self.dir_render / "ultimo_cuadro.png"
        medios.ejecutar(["-sseof", "-0.3", "-i", str(ultimo), "-update", "1", "-q:v", "2", str(cuadro)],
                        descripcion="último cuadro para el cierre")
        tmp = destino.with_suffix(".parcial.mp4")
        medios.ejecutar([
            "-loop", "1", "-framerate", str(FPS), "-t", f"{duracion:.3f}", "-i", str(cuadro),
            "-f", "lavfi", "-t", f"{duracion:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
            "-filter_complex", f"[0:v]scale={W}:{H},boxblur=12:2,eq=brightness=-0.22:saturation=0.8,"
                               f"fade=t=in:st=0:d=0.35,setsar=1,format=yuv420p[v]",
            "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", self.preset, "-crf", self.crf,
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-t", f"{duracion:.3f}", str(tmp)], descripcion="segmento de cierre")
        tmp.replace(destino)
        return destino

    # ------------------------------------------------------------------ paso final

    def _unir(self, nombre: str, segmentos: list[Path], doc: Documento, total: float, salida: Path) -> Path:
        ass = self.dir_render / f"{nombre}.ass"
        doc.guardar(ass)
        args: list[str] = []
        for s in segmentos:
            args += ["-i", str(s.relative_to(self.dir_render)).replace("\\", "/")]
        n = len(segmentos)
        entradas = "".join(f"[{i}:v][{i}:a]" for i in range(n))
        filtros = [f"{entradas}concat=n={n}:v=1:a=1[cv][ca]",
                   f"[cv]ass={ass.name}:fontsdir={self.fontsdir},fade=t=in:st=0:d=0.3,"
                   f"fade=t=out:st={max(0.0, total - 0.6):.3f}:d=0.6[v]"]
        audio = "[ca]"
        if self.g.musica:
            args += ["-stream_loop", "-1", "-i", str(self.g.musica)]
            filtros.append("[ca]asplit=2[prog][clave]")
            filtros.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={self.g.volumen_musica:.2f},"
                           f"atrim=duration={total:.3f}[mus]")
            filtros.append("[mus][clave]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[duck]")
            filtros.append("[prog][duck]amix=inputs=2:normalize=0:duration=first[mx]")
            audio = "[mx]"
        filtros.append(f"{audio}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
                       f"afade=t=out:st={max(0.0, total - 0.6):.3f}:d=0.6[a]")
        args += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
                 "-c:v", "libx264", "-preset", "ultrafast" if self.borrador else "medium",
                 "-crf", "30" if self.borrador else "20", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(salida.resolve())]
        self.log(f"  uniendo {n} segmentos + textos → {salida.relative_to(self.g.dir)}")
        medios.ejecutar(args, cwd=self.dir_render, descripcion=f"paso final ({nombre})")
        return salida

    def _documento(self, W: int, H: int, tramos: list[Tramo], gancho: str, inicio_cierre: float | None, total: float) -> Documento:
        doc = Documento(W, H, self.g.color_acento, self.g.mayusculas)
        if gancho:
            doc.gancho(0.1, min(self.g.duracion_gancho, total), gancho)
        for tr in tramos:
            e, fin = tr.escena, tr.inicio + tr.duracion
            if e.texto:
                doc.texto(tr.inicio + 0.1, fin - 0.1, e.texto)
            if e.dato:
                doc.dato(tr.inicio + 0.3, fin - 0.15, e.dato.valor, e.dato.etiqueta)
            if self.g.subtitulos and tr.voz and e.narracion:
                doc.subtitulos(tr.inicio + 0.15, tr.dur_voz, e.narracion)
        if inicio_cierre is not None and self.g.cierre:
            doc.cierre(inicio_cierre + 0.1, total - 0.1, self.g.cierre, self.g.subcierre)
        return doc

    def _video(self, nombre: str, tramos: list[Tramo], W: int, H: int, encuadre: str, gancho: str, salida: Path) -> Path:
        segmentos = [self._segmento(tr, W, H, encuadre) for tr in tramos]
        total = sum(tr.duracion for tr in tramos)
        inicio_cierre = None
        if self.g.cierre:
            segmentos.append(self._segmento_cierre(segmentos[-1], W, H, self.g.duracion_cierre))
            inicio_cierre, total = total, total + self.g.duracion_cierre
        doc = self._documento(W, H, tramos, gancho, inicio_cierre, total)
        return self._unir(nombre, segmentos, doc, total, salida)

    def _tamano(self, formato: str) -> tuple[int, int]:
        W, H = (1920, 1080) if formato == "horizontal" else (1080, 1920)
        return (W // 2, H // 2) if self.borrador else (W, H)

    # ------------------------------------------------------------------ salidas

    def principal(self) -> Path:
        W, H = self._tamano(self.g.formato)
        tramos = self.tramos()
        self.log(f"Video principal ({self.g.formato}, {W}x{H}, {len(tramos)} escenas):")
        salida = self.dir_entrega / f"{self.g.slug}{self.sufijo}.mp4"
        return self._video("principal", tramos, W, H, "recorte", self.g.gancho, salida)

    def shorts(self) -> list[Path]:
        salidas = []
        W, H = self._tamano("vertical")
        for i, s in enumerate(self.g.shorts, 1):
            tramos = self.tramos(s.escenas, gancho=bool(s.gancho))
            self.log(f"Short {i} «{s.titulo}» ({len(tramos)} escenas, encuadre {s.encuadre}):")
            salida = self.dir_entrega / f"short-{i}{self.sufijo}.mp4"
            salidas.append(self._video(f"short-{i}", tramos, W, H, s.encuadre, s.gancho, salida))
        return salidas

    def miniatura(self) -> Path:
        W, H = MINIATURA[self.g.formato]
        e = self.g.escena(self.g.miniatura_escena)
        fuente = self.r.fuente_visual(e)
        if not fuente:
            raise ErrorRender(f"Falta el recurso de la escena {e.id} para la miniatura")
        cuadro = fuente
        if e.tipo == "video":
            cuadro = self.dir_render / "cuadro_miniatura.png"
            medios.ejecutar(["-ss", f"{medios.duracion(fuente) * 0.45:.2f}", "-i", str(fuente), "-frames:v", "1",
                             str(cuadro)], descripcion="cuadro para la miniatura")
        doc = Documento(W, H, self.g.color_acento)
        doc.miniatura(self.g.miniatura_texto)
        ass = doc.guardar(self.dir_render / "miniatura.ass")
        salida = self.dir_entrega / "miniatura.jpg"
        medios.ejecutar([
            "-i", str(cuadro.resolve()), "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=contrast=1.08:saturation=1.2,"
            f"vignette=PI/5,ass={ass.name}:fontsdir={self.fontsdir}",
            "-frames:v", "1", "-q:v", "2", str(salida.resolve())], cwd=self.dir_render, descripcion="miniatura")
        self.log(f"  miniatura → {salida.relative_to(self.g.dir)}")
        return salida
