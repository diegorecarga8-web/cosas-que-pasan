"""Prueba de punta a punta en modo simulado: no usa la API ni internet, solo ffmpeg."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2 import medios  # noqa: E402
from cqp2.cli import main  # noqa: E402
from cqp2.guion import cargar  # noqa: E402
from cqp2.recursos import Modos, Recursos  # noqa: E402
from cqp2.render import Montaje  # noqa: E402

try:
    medios.ffmpeg()
    HAY_FFMPEG = True
except medios.ErrorMedios:
    HAY_FFMPEG = False

GUION = {
    "titulo": "Prueba de montaje",
    "formato": "horizontal",
    "musica": {"archivo": "musica.mp3", "volumen": 0.2},
    "gancho": {"texto": "Esto *pasó*", "duracion": 2},
    "escenas": [
        {"id": "e01", "prompt": "a village at dawn", "narracion": "Un pueblo entero se quedó dormido.", "duracion": 4,
         "capitulo": "Inicio"},
        {"id": "e02", "tipo": "imagen", "prompt": "an old sign", "narracion": "Se llamaba Kalachi.",
         "efecto": "paneo_izq", "dato": {"valor": "+100", "etiqueta": "personas"}},
        {"id": "e03", "prompt": "a mine", "duracion": 4, "texto": "2015"},
    ],
    "cierre": {"texto": "Cosas que pasan", "subtexto": "Suscríbete", "duracion": 1.5},
    "shorts": [{"titulo": "Corto", "escenas": ["e02", "e03"], "gancho": "¿Por qué?", "encuadre": "relleno"}],
}


@unittest.skipUnless(HAY_FFMPEG, "ffmpeg no disponible")
class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        medios.ejecutar(["-f", "lavfi", "-i", "sine=frequency=330:duration=3", str(cls.dir / "musica.mp3")])
        (cls.dir / "guion.json").write_text(json.dumps(GUION, ensure_ascii=False), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = main(["todo", str(cls.dir / "guion.json"), "--simulado", "--borrador"])
        assert codigo == 0, f"todo devolvió {codigo}"

    def test_entregables(self):
        entrega = self.dir / "entrega"
        principal = entrega / "prueba-de-montaje-borrador.mp4"
        for nombre in (principal.name, "short-1-borrador.mp4", "miniatura.jpg", "metadata.txt"):
            self.assertTrue((entrega / nombre).exists(), nombre)
        self.assertTrue(medios.tiene_audio(principal))
        self.assertEqual(medios.dimensiones(principal), (960, 540))
        self.assertEqual(medios.dimensiones(entrega / "short-1-borrador.mp4"), (540, 960))
        self.assertEqual(medios.dimensiones(entrega / "miniatura.jpg"), (1280, 720))

    def test_duracion_coincide_con_la_linea_de_tiempo(self):
        g = cargar(self.dir / "guion.json")
        tramos = Montaje(g, Recursos(g, Modos.simulado()), borrador=True, log=lambda *_: None).tramos()
        esperado = sum(t.duracion for t in tramos) + g.duracion_cierre
        real = medios.duracion(self.dir / "entrega" / "prueba-de-montaje-borrador.mp4")
        self.assertAlmostEqual(real, esperado, delta=0.15)
        # la escena de video con narración se ajusta a la voz y la imagen dura lo que su voz + respiro
        self.assertLess(tramos[0].duracion, 4.0)
        self.assertAlmostEqual(tramos[1].duracion, max(tramos[1].dur_voz + 0.6, 2.0), delta=0.05)
        self.assertEqual(tramos[2].duracion, 4.0)  # sin narración: el clip completo

    def test_segmentos_en_cache(self):
        segmentos = sorted(p.name for p in (self.dir / "render" / "segmentos").glob("*.mp4"))
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = main(["render", str(self.dir / "guion.json"), "--simulado", "--borrador", "--sin-shorts"])
        self.assertEqual(codigo, 0)
        self.assertEqual(segmentos, sorted(p.name for p in (self.dir / "render" / "segmentos").glob("*.mp4")))

    def test_metadata(self):
        texto = (self.dir / "entrega" / "metadata.txt").read_text(encoding="utf-8")
        self.assertIn("TÍTULO: Prueba de montaje", texto)
        self.assertIn("0:00 Inicio", texto)
        self.assertIn("short-1.mp4 — Corto", texto)


if __name__ == "__main__":
    unittest.main()
