"""Modo navegador: clips hechos en la app de Gemini con la sesión de Google del usuario (sin clave)."""

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2 import medios  # noqa: E402
from cqp2.cli import _modos, main  # noqa: E402

try:
    medios.ffmpeg()
    HAY_FFMPEG = True
except medios.ErrorMedios:
    HAY_FFMPEG = False

GUION = {
    "titulo": "Prueba navegador",
    "escenas": [
        {"id": "e01", "prompt": "a village at dawn", "narracion": "Un pueblo entero se quedó dormido sin aviso.", "duracion": 4},
        {"id": "e02", "tipo": "imagen", "prompt": "an old sign", "narracion": "Se llamaba Kalachi."},
    ],
}


def ejecutar(*args) -> tuple[int, str]:
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
        codigo = main(list(args))
    return codigo, salida.getvalue()


def proyecto() -> Path:
    base = Path(tempfile.mkdtemp())
    (base / "guion.json").write_text(json.dumps(GUION, ensure_ascii=False), encoding="utf-8")
    return base


def clip(ruta: Path, segundos: float = 8) -> Path:
    medios.ejecutar(["-f", "lavfi", "-i", f"testsrc2=s=320x180:d={segundos}:r=24", "-f", "lavfi", "-i",
                     f"sine=frequency=440:duration={segundos}", "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                     "-c:a", "aac", str(ruta)])
    return ruta


class TestModos(unittest.TestCase):
    def args(self, **kw):
        base = {"simulado": False, "navegador": False, "videos": "api", "imagenes": "api", "voz": "api"}
        base.update(kw)
        return argparse.Namespace(**base)

    def test_alias_navegador(self):
        m = _modos(self.args(videos="navegador", imagenes="navegador"))
        self.assertEqual((m.videos, m.imagenes, m.voz), ("app", "app", "api"))

    def test_atajo_navegador_sin_clave(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            m = _modos(self.args(navegador=True))
        self.assertEqual((m.videos, m.imagenes, m.voz), ("app", "app", "no"))

    def test_atajo_navegador_con_clave(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x"}):
            self.assertEqual(_modos(self.args(navegador=True)).voz, "api")
            self.assertEqual(_modos(self.args(navegador=True, voz="no")).voz, "no")


class TestSiguienteYRecoger(unittest.TestCase):
    def test_siguiente_da_el_prompt_y_termina(self):
        base = proyecto()
        codigo, salida = ejecutar("siguiente", str(base / "guion.json"))
        self.assertEqual(codigo, 0)
        self.assertIn("Pendiente 1 de 2: e01 (video)", salida)
        self.assertIn("a village at dawn", salida)
        self.assertIn("recoger", salida)
        (base / "clips").mkdir()
        (base / "clips" / "e01.mp4").write_bytes(b"x")
        _, salida = ejecutar("siguiente", str(base / "guion.json"))
        self.assertIn("Pendiente 1 de 1: e02 (imagen)", salida)
        self.assertIn("Generate an image:", salida)
        (base / "imagenes").mkdir()
        (base / "imagenes" / "e02.png").write_bytes(b"x")
        _, salida = ejecutar("siguiente", str(base / "guion.json"))
        self.assertIn("Nada pendiente", salida)

    @unittest.skipUnless(HAY_FFMPEG, "ffmpeg no disponible")
    def test_recoger_la_descarga_mas_reciente(self):
        base, descargas = proyecto(), Path(tempfile.mkdtemp())
        viejo = clip(descargas / "viejo.mp4", 2)
        os.utime(viejo, (time.time() - 3600, time.time() - 3600))  # fuera de la ventana de 30 min
        anterior = clip(descargas / "anterior.mp4", 2)
        os.utime(anterior, (time.time() - 60, time.time() - 60))
        nuevo = clip(descargas / "Gemini_video.mp4", 3)
        (descargas / "a_medias.mp4.crdownload").write_bytes(b"x")
        codigo, salida = ejecutar("recoger", str(base / "guion.json"), "e01", "--desde", str(descargas))
        self.assertEqual(codigo, 0, salida)
        self.assertTrue((base / "clips" / "e01.mp4").exists())
        self.assertFalse(nuevo.exists())
        self.assertTrue(anterior.exists() and viejo.exists())
        self.assertIn("3.0 s, con audio", salida)

    def test_recoger_imagen_y_errores(self):
        base, descargas = proyecto(), Path(tempfile.mkdtemp())
        codigo, salida = ejecutar("recoger", str(base / "guion.json"), "e02", "--desde", str(descargas))
        self.assertEqual(codigo, 1)
        self.assertIn("No encontré imágenes", salida)
        (descargas / "Gemini_Generated_Image.png").write_bytes(b"png")
        (base / "imagenes").mkdir()
        (base / "imagenes" / "e02.jpg").write_bytes(b"version anterior")
        self.assertEqual(ejecutar("recoger", str(base / "guion.json"), "e02", "--desde", str(descargas))[0], 0)
        self.assertEqual([p.name for p in (base / "imagenes").iterdir()], ["e02.png"])
        self.assertEqual(ejecutar("recoger", str(base / "guion.json"), "e99", "--desde", str(descargas))[0], 1)


@unittest.skipUnless(HAY_FFMPEG, "ffmpeg no disponible")
class TestRenderSinVoz(unittest.TestCase):
    def test_narracion_como_subtitulos_y_voz_faltante(self):
        base = proyecto()
        guion = str(base / "guion.json")
        codigo, salida = ejecutar("render", guion, "--simulado", "--borrador")
        self.assertEqual(codigo, 1)  # faltan recursos: nada generado todavía
        codigo, _ = ejecutar("generar", guion, "--videos", "simulado", "--imagenes", "simulado", "--voz", "no")
        self.assertEqual(codigo, 0)
        codigo, salida = ejecutar("render", guion, "--videos", "simulado", "--imagenes", "simulado", "--voz", "simulado",
                                  "--borrador", "--sin-shorts", "--sin-miniatura")
        self.assertEqual(codigo, 1)
        self.assertIn("e01 (voz)", salida)
        codigo, salida = ejecutar("render", guion, "--videos", "simulado", "--imagenes", "simulado", "--voz", "no",
                                  "--borrador", "--sin-shorts", "--sin-miniatura")
        self.assertEqual(codigo, 0, salida)
        ass = (base / "render" / "principal.ass").read_text(encoding="utf-8")
        self.assertGreaterEqual(ass.count(",Subtitulo,,"), 3)
        video = base / "entrega" / "prueba-navegador-borrador.mp4"
        # sin voz, cada escena dura lo que toma leer su narración (+ respiro)
        self.assertAlmostEqual(medios.duracion(video), (3.4 + 0.5) + max(1.1 + 0.6, 2.0), delta=0.2)


if __name__ == "__main__":
    unittest.main()
