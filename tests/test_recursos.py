import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2 import precios  # noqa: E402
from cqp2.guion import interpretar  # noqa: E402
from cqp2.recursos import ErrorRecursos, FaltaConfirmar, Modos, Recursos  # noqa: E402

DATOS = {
    "titulo": "Prueba",
    "escenas": [
        {"id": "e01", "prompt": "a snowy village", "narracion": "Un pueblo entero se quedó dormido.", "duracion": 4},
        {"id": "e02", "tipo": "imagen", "prompt": "an old sign", "narracion": "Se llamaba Kalachi."},
        {"id": "e03", "prompt": "a mine", "duracion": 8, "imagen_inicial": "@e02"},
    ],
}


def recursos(modos: Modos, datos: dict = DATOS) -> Recursos:
    base = Path(tempfile.mkdtemp())
    return Recursos(interpretar(datos, base / "guion.json"), modos)


class TestRecursos(unittest.TestCase):
    def test_claves_estables_y_sensibles_al_prompt(self):
        r = recursos(Modos())
        e1 = r.g.escena("e01")
        self.assertEqual(r.clave_video(e1), r.clave_video(e1))
        antes = r.clave_video(r.g.escena("e03"))
        r.g.escena("e02").prompt = "a different sign"  # cambia la imagen de la que parte e03
        self.assertNotEqual(antes, r.clave_video(r.g.escena("e03")))
        e1.prompt = "otra cosa"
        self.assertNotEqual(r.clave_video(e1), r.clave_video(r.g.escena("e03")))

    def test_estimacion(self):
        r = recursos(Modos())
        partidas = r.estimar()
        tipos = sorted(p.tipo for p in partidas)
        self.assertEqual(tipos, ["imagen", "video", "video", "voz", "voz"])
        videos = sum(p.usd for p in partidas if p.tipo == "video")
        self.assertAlmostEqual(videos, (4 + 8) * precios.PRECIOS["video_por_segundo"]["veo-3.1-lite-generate-preview"]["720p"])
        self.assertEqual(recursos(Modos.simulado()).estimar(), [])
        self.assertEqual(recursos(Modos(videos="app", imagenes="app", voz="no")).estimar(), [])

    def test_no_gasta_sin_confirmar(self):
        r = recursos(Modos())
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "falsa"}):
            with mock.patch.object(Recursos, "_api", side_effect=AssertionError("no debía llamar a la API")):
                with self.assertRaises(FaltaConfirmar):
                    r.generar()
                with self.assertRaises(ErrorRecursos) as ctx:
                    r.generar(confirmar=True, max_usd=0.10)
                self.assertIn("supera el tope", str(ctx.exception))

    def test_sin_clave(self):
        r = recursos(Modos())
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ErrorRecursos) as ctx:
                r.generar(confirmar=True)
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_modo_app(self):
        r = recursos(Modos(videos="app", imagenes="app", voz="no"))
        self.assertEqual(r.faltantes_app(), ["clips/e01.mp4", "imagenes/e02.png", "clips/e03.mp4"])
        (r.dir / "clips").mkdir()
        (r.dir / "clips" / "e01.mov").write_bytes(b"x")
        self.assertEqual(r.video(r.g.escena("e01")).name, "e01.mov")
        self.assertNotIn("clips/e01.mp4", r.faltantes_app())

    def test_voz_propia_tiene_prioridad(self):
        r = recursos(Modos())
        (r.dir / "voz").mkdir()
        (r.dir / "voz" / "e01.wav").write_bytes(b"x")
        self.assertEqual(r.voz(r.g.escena("e01")).name, "e01.wav")
        self.assertNotIn(("voz", "e01"), [(t, e.id) for t, e in r.pendientes()])

    def test_precios_del_proyecto(self):
        r = recursos(Modos())
        (r.dir / "precios.json").write_text('{"imagen": {"gemini-3.1-flash-image": 1.0}}', encoding="utf-8")
        tabla = precios.cargar_precios(r.dir)
        self.assertEqual(tabla["imagen"]["gemini-3.1-flash-image"], 1.0)
        self.assertIn("veo-3.1-lite-generate-preview", tabla["video_por_segundo"])


if __name__ == "__main__":
    unittest.main()
