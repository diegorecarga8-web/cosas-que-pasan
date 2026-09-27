"""Textos en pantalla como subtítulos ASS (los dibuja libass dentro de ffmpeg).

Gancho, textos de escena, tarjetas de datos, subtítulos de la narración, cierre, miniatura y
la placa de los recursos simulados. Las medidas son proporcionales al lado corto del video,
así el mismo guion se ve bien en horizontal y en vertical.
"""

from __future__ import annotations

import re
from pathlib import Path

BLANCO = "&H00FFFFFF"
NEGRO = "&H00000000"
SOMBRA = "&H96000000"
FONDO_TARJETA = "&H2A140E0A"  # azul casi negro, ~84% opaco


def tiempo(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def color_ass(hex_rgb: str, alfa: int = 0) -> str:
    r, g, b = hex_rgb[1:3], hex_rgb[3:5], hex_rgb[5:7]
    return f"&H{alfa:02X}{b}{g}{r}".upper()


def limpiar(texto: str) -> str:
    """Evita que el texto del guion se interprete como etiquetas ASS."""
    texto = texto.replace("\\", "/").replace("{", "(").replace("}", ")")
    return re.sub(r"\s*\n\s*", r"\\N", texto.strip())


def resaltar(texto: str, acento: str, base: str = BLANCO) -> str:
    """Las palabras entre *asteriscos* se pintan con el color de acento."""
    return re.sub(r"\*([^*]+)\*", lambda m: "{\\1c" + acento + "&}" + m.group(1) + "{\\1c" + base + "&}", texto)


def sin_marcas(texto: str) -> str:
    """Texto sin los *asteriscos* de resaltado (lo que se envía a la voz)."""
    return texto.replace("*", "")


def marcar_por_palabra(texto: str) -> str:
    """'*300 personas*' -> '*300* *personas*' para que el resaltado sobreviva al partir frases."""
    return re.sub(r"\*([^*]+)\*", lambda m: " ".join(f"*{p}*" for p in m.group(1).split()), texto)


def partir_frases(texto: str, max_palabras: int, max_caracteres: int) -> list[str]:
    frases: list[str] = []
    actual: list[str] = []
    for palabra in texto.split():
        candidato = actual + [palabra]
        if actual and (len(candidato) > max_palabras or len(" ".join(candidato)) > max_caracteres):
            frases.append(" ".join(actual))
            candidato = [palabra]
        actual = candidato
        if re.search(r"[.!?¡¿;:…]$", palabra) or (palabra.endswith(",") and len(actual) >= 3):
            frases.append(" ".join(actual))
            actual = []
    if actual:
        frases.append(" ".join(actual))
    return frases


def repartir(frases: list[str], inicio: float, duracion: float) -> list[tuple[float, float, str]]:
    """Reparte el tiempo de la narración entre las frases según su largo."""
    if not frases or duracion <= 0:
        return []
    pesos = [len(f) + 3 for f in frases]
    total = sum(pesos)
    tramos, t = [], inicio
    for frase, peso in zip(frases, pesos):
        dur = max(0.35, duracion * peso / total)
        tramos.append((t, t + dur, frase))
        t += dur
    escala = duracion / (t - inicio)  # compensa los mínimos para terminar justo al final
    return [(inicio + (a - inicio) * escala, inicio + (b - inicio) * escala, f) for a, b, f in tramos]


def _rect_redondeado(ancho: float, alto: float, radio: float) -> str:
    w, h, r = round(ancho), round(alto), round(min(radio, ancho / 2, alto / 2))
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


class Documento:
    def __init__(self, ancho: int, alto: int, acento: str = "#FFD23F", mayusculas: bool = False):
        self.W, self.H = ancho, alto
        self.base = min(ancho, alto)
        self.vertical = alto > ancho
        self.acento = color_ass(acento)
        self.mayusculas = mayusculas
        self._estilos: list[str] = []
        self._eventos: list[str] = []
        b, W, H = self.base, ancho, alto
        margen_lateral = round(0.07 * W)
        self._estilo("Gancho", "Anton", 0.105 * b, BLANCO, 0.0065 * b, 3, 5, margen_lateral, round(0.05 * H))
        self._estilo("Texto", "Anton", 0.085 * b, BLANCO, 0.0055 * b, 3, 8, margen_lateral,
                     round((0.13 if self.vertical else 0.09) * H))
        self._estilo("Subtitulo", "Poppins ExtraBold", (0.066 if self.vertical else 0.05) * b, BLANCO, 0.0055 * b, 2, 2,
                     round(0.08 * W), round((0.25 if self.vertical else 0.065) * H))
        self._estilo("DatoValor", "Anton", 0.12 * b, self.acento, 0, 0, 7, 0, 0)
        self._estilo("DatoEtiqueta", "Poppins", 0.044 * b, BLANCO, 0, 0, 7, 0, 0, negrita=True)
        self._estilo("Tarjeta", "Poppins", 20, FONDO_TARJETA, 0, 0, 7, 0, 0)
        self._estilo("Cierre", "Anton", 0.1 * b, BLANCO, 0.006 * b, 3, 5, margen_lateral, 0)
        self._estilo("Subcierre", "Poppins", 0.042 * b, self.acento, 0.004 * b, 2, 8, margen_lateral, 0, negrita=True)
        self._estilo("Miniatura", "Anton", 0.2 * b, BLANCO, 0.012 * b, 6, 2, round(0.05 * W), round(0.07 * H))
        self._estilo("Placa", "Poppins", 0.04 * b, BLANCO, 0.003 * b, 0, 7, round(0.05 * W), round(0.06 * H), negrita=True)

    def _estilo(self, nombre, fuente, tamano, primario, contorno, sombra, alineacion, margen_lr, margen_v, negrita=False):
        self._estilos.append(
            f"Style: {nombre},{fuente},{round(tamano)},{primario},&H000000FF,{NEGRO},{SOMBRA},"
            f"{-1 if negrita else 0},0,0,0,100,100,0,0,1,{round(contorno, 1)},{sombra},{alineacion},"
            f"{margen_lr},{margen_lr},{margen_v},1"
        )

    def evento(self, inicio: float, fin: float, estilo: str, texto: str, capa: int = 0) -> None:
        if fin - inicio < 0.05:
            return
        self._eventos.append(f"Dialogue: {capa},{tiempo(inicio)},{tiempo(fin)},{estilo},,0,0,0,,{texto}")

    def _caja(self, texto: str) -> str:
        texto = limpiar(texto)
        return texto.upper() if self.mayusculas else texto

    # ---- piezas ----

    def gancho(self, inicio: float, fin: float, texto: str) -> None:
        anim = r"{\fad(120,250)\fscx60\fscy60\t(0,180,\fscx106\fscy106)\t(180,280,\fscx100\fscy100)}"
        self.evento(inicio, fin, "Gancho", anim + resaltar(limpiar(texto).upper(), self.acento), capa=5)

    def texto(self, inicio: float, fin: float, texto: str) -> None:
        anim = r"{\fad(150,200)\fscx85\fscy85\t(0,160,\fscx100\fscy100)}"
        self.evento(inicio, fin, "Texto", anim + resaltar(limpiar(texto).upper(), self.acento), capa=4)

    def subtitulos(self, inicio: float, duracion: float, narracion: str) -> None:
        maxp, maxc = (4, 24) if self.vertical else (7, 42)
        frases = partir_frases(marcar_por_palabra(narracion), maxp, maxc)
        for a, b, frase in repartir(frases, inicio, duracion):
            self.evento(a, b, "Subtitulo", resaltar(self._caja(frase), self.acento), capa=3)

    def dato(self, inicio: float, fin: float, valor: str, etiqueta: str = "") -> None:
        b = self.base
        pad, tv, te = 0.026 * b, 0.12 * b, 0.044 * b
        lineas = partir_frases(etiqueta, 5, 22) if etiqueta else []
        # anchos medidos con libass: Anton ~0.30 y Poppins Bold ~0.42 del tamaño por carácter
        ancho_valor = len(valor) * tv * 0.30
        ancho_etiqueta = max((len(l) for l in lineas), default=0) * te * 0.42
        ancho = max(ancho_valor, ancho_etiqueta, 0.12 * b) + 2 * pad
        alto = pad * 0.55 + tv * 1.0 + len(lineas) * te * 1.2 + pad * 0.75
        if self.vertical:
            x0, y0 = (self.W - ancho) / 2, 0.15 * self.H
        else:
            x0, y0 = 0.045 * self.W, 0.24 * self.H
        dx = 0.04 * b
        barra = 0.008 * b

        def mov(x, y):
            return rf"\move({round(x - dx)},{round(y)},{round(x)},{round(y)},0,280)"

        fade = r"\fad(200,220)"
        self.evento(inicio, fin, "Tarjeta", "{" + mov(x0, y0) + fade + r"\p1}" + _rect_redondeado(ancho, alto, 0.02 * b) + r"{\p0}", capa=6)
        self.evento(inicio, fin, "Tarjeta", "{" + mov(x0, y0) + fade + r"\1c" + self.acento + r"&\p1}" + _rect_redondeado(barra, alto, barra / 2) + r"{\p0}", capa=7)
        self.evento(inicio, fin, "DatoValor", "{" + mov(x0 + pad, y0 + pad * 0.45) + fade + "}" + limpiar(valor), capa=8)
        if lineas:
            y_et = y0 + pad * 0.45 + tv * 1.0
            self.evento(inicio, fin, "DatoEtiqueta", "{" + mov(x0 + pad, y_et) + fade + "}" + r"\N".join(limpiar(l) for l in lineas), capa=8)

    def cierre(self, inicio: float, fin: float, texto: str, subtexto: str = "") -> None:
        anim = r"{\fad(250,300)\fscx80\fscy80\t(0,250,\fscx100\fscy100)}"
        self.evento(inicio, fin, "Cierre", anim + resaltar(limpiar(texto).upper(), self.acento), capa=5)
        if subtexto:
            y = round(0.5 * self.H + 0.1 * self.base)
            self.evento(inicio + 0.2, fin, "Subcierre", rf"{{\an8\pos({self.W // 2},{y})\fad(250,300)}}" + limpiar(subtexto), capa=5)

    def miniatura(self, texto: str) -> None:
        self.evento(0, 10, "Miniatura", resaltar(limpiar(texto).upper(), self.acento), capa=5)

    def placa(self, texto: str) -> None:
        self.evento(0, 3600, "Placa", limpiar(texto), capa=5)

    # ---- salida ----

    def contenido(self) -> str:
        return "\n".join([
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {self.W}",
            f"PlayResY: {self.H}",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding",
            *self._estilos,
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *self._eventos,
            "",
        ])

    def guardar(self, ruta: Path) -> Path:
        ruta.write_text(self.contenido(), encoding="utf-8")
        return ruta
