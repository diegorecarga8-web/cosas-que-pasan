"""Formato del guion (JSON) de Cosas que pasan 2: carga, valores por defecto y validación.

La referencia completa del formato está en referencia/formato-guion.md.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

FORMATOS = {"horizontal": (1920, 1080, "16:9"), "vertical": (1080, 1920, "9:16")}
TIPOS = ("video", "imagen")
EFECTOS = ("zoom_in", "zoom_out", "paneo_izq", "paneo_der", "ninguno")
ENCUADRES = ("recorte", "relleno")
RESOLUCIONES = ("720p", "1080p", "4k")
DURACIONES_VEO = (4, 6, 8)
PALABRAS_POR_SEGUNDO = 2.6  # ritmo de una narración ágil en español

MODELO_VIDEO = "veo-3.1-lite-generate-preview"
MODELO_IMAGEN = "gemini-3.1-flash-image"
MODELO_VOZ = "gemini-3.1-flash-tts-preview"
VOZ = "Charon"
INDICACIONES_VOZ = "Narra en español latino neutro, con tono intrigante y cercano, a ritmo ágil"
EVITAR = "on-screen text, subtitles, captions, letters, watermark, logo, distorted faces, extra fingers"
COLOR_ACENTO = "#FFD23F"


class ErrorGuion(ValueError):
    pass


@dataclass
class Dato:
    valor: str
    etiqueta: str = ""


@dataclass
class Escena:
    id: str
    tipo: str
    prompt: str
    narracion: str = ""
    duracion: float = 4.0
    duracion_fija: bool = False  # True si el guion la indicó (imágenes: no se ajusta a la voz)
    texto: str = ""
    dato: Dato | None = None
    efecto: str = "ninguno"
    sacudida: bool | None = None  # None = por defecto (sí en la primera escena si hay gancho)
    volumen_clip: float | None = None
    imagen_inicial: str = ""
    referencias: list[str] = field(default_factory=list)
    capitulo: str = ""
    mantener_clip: bool = False


@dataclass
class Short:
    titulo: str
    escenas: list[str]
    gancho: str = ""
    encuadre: str = "recorte"


@dataclass
class Guion:
    ruta: Path
    titulo: str
    slug: str
    formato: str
    estilo_visual: str
    evitar: str
    modelo_video: str
    resolucion: str
    modelo_imagen: str
    voz_activa: bool
    modelo_voz: str
    voz: str
    indicaciones_voz: str
    musica: Path | None
    volumen_musica: float
    subtitulos: bool
    mayusculas: bool
    color_acento: str
    gancho: str
    duracion_gancho: float
    cierre: str
    subcierre: str
    duracion_cierre: float
    miniatura_texto: str
    miniatura_escena: str
    escenas: list[Escena]
    shorts: list[Short]
    descripcion: str
    etiquetas: list[str]
    advertencias: list[str] = field(default_factory=list)

    @property
    def dir(self) -> Path:
        return self.ruta.parent

    @property
    def tamano(self) -> tuple[int, int]:
        ancho, alto, _ = FORMATOS[self.formato]
        return ancho, alto

    @property
    def aspecto(self) -> str:
        return FORMATOS[self.formato][2]

    def escena(self, id_: str) -> Escena:
        for e in self.escenas:
            if e.id == id_:
                return e
        raise KeyError(id_)

    def prompt_visual(self, escena: Escena) -> str:
        """Prompt completo que se envía al modelo: descripción de la escena + estilo común."""
        partes = [escena.prompt.strip().rstrip(".")]
        if self.estilo_visual:
            partes.append(self.estilo_visual.strip().rstrip("."))
        if escena.tipo == "video" and escena.narracion:
            partes.append("No dialogue or speech, only ambient sound and effects")  # la voz la pone la narración
        return ". ".join(partes) + "."


def slugificar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base[:60].strip("-") or "video"


def estimar_narracion(texto: str) -> float:
    """Segundos aproximados que dura una narración (antes de generar la voz)."""
    palabras = len(texto.split())
    return round(palabras / PALABRAS_POR_SEGUNDO + 0.3, 1) if palabras else 0.0


def duracion_veo_para(segundos: float) -> int:
    """La duración de Veo más corta que cubre `segundos`; 8 si nada alcanza.

    El margen es chico a propósito: si la voz real dura un poco más, el montaje congela el
    último cuadro unas décimas, que es más barato que pagar 2 s extra de Veo por escena.
    """
    for d in DURACIONES_VEO:
        if d >= segundos + 0.2:
            return d
    return DURACIONES_VEO[-1]


def _texto(d: dict, clave: str, por_defecto: str = "") -> str:
    valor = d.get(clave, por_defecto)
    if valor is None:
        return por_defecto
    if not isinstance(valor, str):
        raise ErrorGuion(f"'{clave}' debe ser texto")
    return valor.strip()


def _numero(d: dict, clave: str, por_defecto: float | None, errores: list[str], donde: str) -> float | None:
    valor = d.get(clave, por_defecto)
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        errores.append(f"{donde}: '{clave}' debe ser un número")
        return por_defecto
    return float(valor)


def cargar(ruta: str | Path) -> Guion:
    ruta = Path(ruta).resolve()
    if not ruta.exists():
        raise ErrorGuion(f"No existe el guion {ruta}")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErrorGuion(f"El guion no es JSON válido (línea {e.lineno}, columna {e.colno}): {e.msg}") from None
    if not isinstance(datos, dict):
        raise ErrorGuion("El guion debe ser un objeto JSON")
    return interpretar(datos, ruta)


def interpretar(datos: dict, ruta: Path) -> Guion:
    errores: list[str] = []
    avisos: list[str] = []
    base = ruta.parent

    titulo = _texto(datos, "titulo")
    if not titulo:
        errores.append("Falta 'titulo'")
    formato = _texto(datos, "formato", "horizontal")
    if formato not in FORMATOS:
        errores.append(f"'formato' debe ser uno de {list(FORMATOS)}")
        formato = "horizontal"

    video = datos.get("video") or {}
    imagen = datos.get("imagen") or {}
    voz = datos.get("voz") or {}
    musica = datos.get("musica") or {}
    estilo = datos.get("estilo") or {}
    gancho = datos.get("gancho") or {}
    cierre = datos.get("cierre") or {}
    miniatura = datos.get("miniatura") or {}
    metadata = datos.get("metadata") or {}
    for nombre, valor in (("video", video), ("imagen", imagen), ("voz", voz), ("musica", musica), ("estilo", estilo),
                          ("gancho", gancho), ("cierre", cierre), ("miniatura", miniatura), ("metadata", metadata)):
        if not isinstance(valor, dict):
            raise ErrorGuion(f"'{nombre}' debe ser un objeto JSON")

    resolucion = _texto(video, "resolucion", "720p").lower()
    if resolucion not in RESOLUCIONES:
        errores.append(f"'video.resolucion' debe ser uno de {list(RESOLUCIONES)}")
        resolucion = "720p"

    ruta_musica = None
    if _texto(musica, "archivo"):
        ruta_musica = (base / _texto(musica, "archivo")).resolve()
        if not ruta_musica.exists():
            errores.append(f"No existe la música {ruta_musica}")

    color = _texto(estilo, "color_acento", COLOR_ACENTO)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        errores.append("'estilo.color_acento' debe tener la forma #RRGGBB")
        color = COLOR_ACENTO

    escenas = _escenas(datos.get("escenas"), base, errores, avisos)
    ids = {e.id for e in escenas}

    shorts: list[Short] = []
    for i, s in enumerate(datos.get("shorts") or [], 1):
        if not isinstance(s, dict):
            errores.append(f"shorts[{i}] debe ser un objeto")
            continue
        lista = s.get("escenas") or []
        desconocidas = [x for x in lista if x not in ids]
        if not lista:
            errores.append(f"shorts[{i}]: indica 'escenas' (lista de ids)")
        if desconocidas:
            errores.append(f"shorts[{i}]: escenas desconocidas {desconocidas}")
        encuadre = _texto(s, "encuadre", "recorte")
        if encuadre not in ENCUADRES:
            errores.append(f"shorts[{i}]: 'encuadre' debe ser uno de {list(ENCUADRES)}")
        shorts.append(Short(titulo=_texto(s, "titulo") or f"Short {i}", escenas=list(lista),
                            gancho=_texto(s, "gancho"), encuadre=encuadre))
    if shorts and formato == "horizontal" and resolucion == "720p":
        avisos.append("Los shorts se recortan en vertical desde clips horizontales de 720p y pierden nitidez; "
                      "para shorts nítidos usa formato vertical o 'video.resolucion': '1080p'.")

    voz_activa = voz.get("activar")
    if voz_activa is None:
        voz_activa = any(e.narracion for e in escenas)

    texto_gancho = _texto(gancho, "texto")
    if len(texto_gancho) > 70:
        avisos.append(f"El gancho tiene {len(texto_gancho)} caracteres; en pantalla funciona mejor con menos de 60.")
    escena_mini = _texto(miniatura, "escena") or (escenas[0].id if escenas else "")
    if escenas and escena_mini not in ids:
        errores.append(f"'miniatura.escena' no existe: {escena_mini}")

    for i, e in enumerate(escenas):
        if e.sacudida is None:  # el gancho entra con impacto salvo que el guion diga lo contrario
            e.sacudida = i == 0 and bool(texto_gancho)

    etiquetas = metadata.get("etiquetas") or []
    if not isinstance(etiquetas, list):
        errores.append("'metadata.etiquetas' debe ser una lista")
        etiquetas = []

    if errores:
        raise ErrorGuion("El guion tiene errores:\n- " + "\n- ".join(errores))

    return Guion(
        ruta=ruta,
        titulo=titulo,
        slug=slugificar(_texto(datos, "slug") or titulo),
        formato=formato,
        estilo_visual=_texto(datos, "estilo_visual"),
        evitar=_texto(datos, "evitar", EVITAR),
        modelo_video=_texto(video, "modelo", MODELO_VIDEO),
        resolucion=resolucion,
        modelo_imagen=_texto(imagen, "modelo", MODELO_IMAGEN),
        voz_activa=bool(voz_activa),
        modelo_voz=_texto(voz, "modelo", MODELO_VOZ),
        voz=_texto(voz, "voz", VOZ),
        indicaciones_voz=_texto(voz, "indicaciones", INDICACIONES_VOZ),
        musica=ruta_musica,
        volumen_musica=float(musica.get("volumen", 0.15)),
        subtitulos=bool(datos.get("subtitulos", True)),
        mayusculas=bool(estilo.get("mayusculas", False)),
        color_acento=color,
        gancho=texto_gancho,
        duracion_gancho=float(gancho.get("duracion", 3.0)),
        cierre=_texto(cierre, "texto"),
        subcierre=_texto(cierre, "subtexto"),
        duracion_cierre=float(cierre.get("duracion", 3.0)),
        miniatura_texto=_texto(miniatura, "texto") or titulo,
        miniatura_escena=escena_mini,
        escenas=escenas,
        shorts=shorts,
        descripcion=_texto(metadata, "descripcion"),
        etiquetas=[str(x) for x in etiquetas],
        advertencias=avisos,
    )


def _escenas(lista, base: Path, errores: list[str], avisos: list[str]) -> list[Escena]:
    if not isinstance(lista, list) or not lista:
        errores.append("'escenas' debe ser una lista con al menos una escena")
        return []
    escenas: list[Escena] = []
    vistos: set[str] = set()
    for i, d in enumerate(lista, 1):
        donde = f"escena {i}"
        if not isinstance(d, dict):
            errores.append(f"{donde}: debe ser un objeto")
            continue
        id_ = _texto(d, "id") or f"e{i:02d}"
        donde = f"escena {id_}"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", id_):
            errores.append(f"{donde}: el id solo puede tener letras, números, '-' o '_'")
        if id_ in vistos:
            errores.append(f"{donde}: id repetido")
        vistos.add(id_)

        tipo = _texto(d, "tipo", "video")
        if tipo not in TIPOS:
            errores.append(f"{donde}: 'tipo' debe ser uno de {list(TIPOS)}")
            tipo = "video"
        prompt = _texto(d, "prompt")
        if not prompt:
            errores.append(f"{donde}: falta 'prompt' (descripción visual, idealmente en inglés)")
        narracion = _texto(d, "narracion")
        estimada = estimar_narracion(narracion)
        mantener = bool(d.get("mantener_clip", False))

        dur = _numero(d, "duracion", None, errores, donde)
        fija = dur is not None
        if tipo == "video":
            if dur is None:
                dur = duracion_veo_para(estimada) if narracion else 4
            elif int(dur) != dur or int(dur) not in DURACIONES_VEO:
                errores.append(f"{donde}: en video 'duracion' debe ser 4, 6 u 8 (segundos de Veo)")
                dur = 8
            if narracion and estimada > dur + 1:
                avisos.append(f"{donde}: la narración (~{estimada:.1f} s) supera el clip ({dur:.0f} s); "
                              "se congelará el último cuadro. Divide la escena o acorta el texto.")
            elif narracion and not mantener and dur - estimada > 2.5:
                avisos.append(f"{donde}: pagarás {dur:.0f} s de video y la narración usa ~{estimada:.1f} s; "
                              f"considera 'duracion': {duracion_veo_para(estimada)}.")
        else:
            if dur is None:
                dur = max(2.5, estimada + 0.4) if narracion else 4.0
            elif dur <= 0:
                errores.append(f"{donde}: 'duracion' debe ser mayor que 0")
                dur = 4.0

        efecto = _texto(d, "efecto", "zoom_in" if tipo == "imagen" else "ninguno")
        if efecto not in EFECTOS:
            errores.append(f"{donde}: 'efecto' debe ser uno de {list(EFECTOS)}")
            efecto = "ninguno"
        if tipo == "video" and efecto != "ninguno":
            avisos.append(f"{donde}: 'efecto' solo se aplica a imágenes; en video usa 'sacudida' o describe el movimiento de cámara en el prompt.")

        dato = None
        if d.get("dato") is not None:
            dd = d["dato"]
            if not isinstance(dd, dict) or not str(dd.get("valor", "")).strip():
                errores.append(f"{donde}: 'dato' necesita al menos 'valor'")
            else:
                dato = Dato(valor=str(dd["valor"]).strip(), etiqueta=str(dd.get("etiqueta", "")).strip())

        inicial = _texto(d, "imagen_inicial")
        if inicial and tipo != "video":
            errores.append(f"{donde}: 'imagen_inicial' solo aplica a escenas de video")
        if inicial and not inicial.startswith("@") and not (base / inicial).exists():
            errores.append(f"{donde}: no existe la imagen inicial {base / inicial}")

        referencias = d.get("referencias") or []
        if not isinstance(referencias, list):
            errores.append(f"{donde}: 'referencias' debe ser una lista de rutas")
            referencias = []
        if referencias and tipo != "video":
            errores.append(f"{donde}: 'referencias' solo aplica a escenas de video")
        if len(referencias) > 3:
            errores.append(f"{donde}: Veo acepta hasta 3 imágenes de referencia")
        for r in referencias:
            if not (base / str(r)).exists():
                errores.append(f"{donde}: no existe la referencia {base / str(r)}")

        volumen = _numero(d, "volumen_clip", None, errores, donde)
        texto = _texto(d, "texto")
        if len(texto) > 45:
            avisos.append(f"{donde}: el 'texto' en pantalla es largo ({len(texto)} caracteres).")

        escenas.append(Escena(
            id=id_, tipo=tipo, prompt=prompt, narracion=narracion, duracion=float(dur), duracion_fija=fija,
            texto=texto, dato=dato, efecto=efecto,
            sacudida=None if d.get("sacudida") is None else bool(d["sacudida"]),
            volumen_clip=volumen, imagen_inicial=inicial, referencias=[str(r) for r in referencias],
            capitulo=_texto(d, "capitulo"), mantener_clip=mantener,
        ))

    por_id = {e.id: e for e in escenas}
    for e in escenas:
        if e.imagen_inicial.startswith("@"):
            fuente = por_id.get(e.imagen_inicial[1:])
            if fuente is None or fuente.tipo != "imagen":
                errores.append(f"escena {e.id}: 'imagen_inicial' {e.imagen_inicial} debe apuntar a una escena de tipo imagen")
    return escenas
