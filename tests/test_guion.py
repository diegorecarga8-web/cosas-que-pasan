import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2.guion import ErrorGuion, cargar, duracion_veo_para, estimar_narracion, interpretar, slugificar  # noqa: E402

PLANTILLA = SKILL / "plantillas" / "guion_ejemplo.json"


def guion(datos: dict, base: Path | None = None):
    base = base or Path(tempfile.mkdtemp())
    return interpretar(datos, base / "guion.json")


class TestGuion(unittest.TestCase):
    def test_plantilla_es_valida(self):
        g = cargar(PLANTILLA)
        self.assertEqual(len(g.escenas), 6)
        self.assertEqual(g.aspecto, "16:9")
        self.assertEqual(g.escena("e01").duracion, 6)  # elegida según la narración
        self.assertTrue(g.escena("e01").sacudida)  # primera escena con gancho
        self.assertTrue(g.escena("e05").sacudida)  # explícita
        self.assertFalse(g.escena("e02").sacudida)
        self.assertEqual(g.escena("e03").efecto, "zoom_in")
        self.assertEqual(g.shorts[0].escenas, ["e01", "e02", "e05"])

    def test_errores_juntos(self):
        with self.assertRaises(ErrorGuion) as ctx:
            guion({"escenas": [
                {"id": "a", "prompt": "x", "duracion": 5},
                {"id": "b", "tipo": "video", "prompt": "y", "imagen_inicial": "@a"},
                {"id": "c", "tipo": "raro", "prompt": ""},
            ], "shorts": [{"escenas": ["zz"]}]})
        msg = str(ctx.exception)
        for fragmento in ("titulo", "4, 6 u 8", "tipo imagen", "'tipo'", "falta 'prompt'", "desconocidas"):
            self.assertIn(fragmento, msg)

    def test_sacudida_explicita_se_respeta(self):
        g = guion({"titulo": "t", "gancho": {"texto": "hola"},
                   "escenas": [{"prompt": "x", "sacudida": False}, {"prompt": "y"}]})
        self.assertFalse(g.escenas[0].sacudida)

    def test_duracion_veo(self):
        self.assertEqual(duracion_veo_para(3.5), 4)
        self.assertEqual(duracion_veo_para(3.9), 6)
        self.assertEqual(duracion_veo_para(5.8), 6)
        self.assertEqual(duracion_veo_para(12), 8)

    def test_estimar_y_slug(self):
        self.assertEqual(estimar_narracion("uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece"), 5.3)
        self.assertEqual(estimar_narracion(""), 0.0)
        self.assertEqual(slugificar("¿Qué pasó en Kalachi?"), "que-paso-en-kalachi")

    def test_prompt_visual(self):
        g = guion({"titulo": "t", "estilo_visual": "film look.", "escenas": [
            {"prompt": "a village.", "narracion": "hola"}, {"tipo": "imagen", "prompt": "a sign", "narracion": "x"}]})
        self.assertEqual(g.prompt_visual(g.escenas[0]),
                         "a village. film look. No dialogue or speech, only ambient sound and effects.")
        self.assertEqual(g.prompt_visual(g.escenas[1]), "a sign. film look.")

    def test_avisos_de_duracion(self):
        largo = " ".join(["palabra"] * 30)
        g = guion({"titulo": "t", "escenas": [{"prompt": "x", "duracion": 4, "narracion": largo},
                                              {"prompt": "y", "duracion": 8, "narracion": "hola"}]})
        self.assertTrue(any("supera el clip" in a for a in g.advertencias))
        self.assertTrue(any("pagarás 8 s" in a for a in g.advertencias))

    def test_json_invalido(self):
        ruta = Path(tempfile.mkdtemp()) / "guion.json"
        ruta.write_text("{ nope", encoding="utf-8")
        with self.assertRaises(ErrorGuion):
            cargar(ruta)

    def test_rutas_relativas_al_proyecto(self):
        base = Path(tempfile.mkdtemp())
        (base / "ref.png").write_bytes(b"x")
        g = guion({"titulo": "t", "escenas": [{"prompt": "x", "referencias": ["ref.png"]}]}, base)
        self.assertEqual(g.escenas[0].referencias, ["ref.png"])
        with self.assertRaises(ErrorGuion):
            guion({"titulo": "t", "escenas": [{"prompt": "x", "referencias": ["no.png"]}]}, base)

    def test_plantilla_es_json_valido(self):
        json.loads(PLANTILLA.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
