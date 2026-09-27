import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2.subtitulos import (Documento, color_ass, limpiar, marcar_por_palabra, partir_frases,  # noqa: E402
                             repartir, resaltar, sin_marcas, tiempo)


class TestSubtitulos(unittest.TestCase):
    def test_tiempo_y_color(self):
        self.assertEqual(tiempo(0), "0:00:00.00")
        self.assertEqual(tiempo(3661.237), "1:01:01.24")
        self.assertEqual(color_ass("#FFD23F"), "&H003FD2FF")

    def test_partir_frases(self):
        frases = partir_frases("En 1954, un pueblo entero de los Andes amaneció vacío. Nadie supo por qué.", 4, 24)
        self.assertEqual(frases[0], "En 1954, un pueblo")  # la coma solo corta frases de 3+ palabras
        self.assertEqual(frases[2], "amaneció vacío.")
        self.assertIn("vacío.", " ".join(frases))
        self.assertTrue(all(len(f.split()) <= 4 for f in frases))

    def test_repartir_cubre_la_narracion(self):
        tramos = repartir(["uno", "dos tres cuatro", "cinco"], 10.0, 3.0)
        self.assertAlmostEqual(tramos[0][0], 10.0)
        self.assertAlmostEqual(tramos[-1][1], 13.0)
        for (a, b, _), (c, _, _) in zip(tramos, tramos[1:]):
            self.assertLess(a, b)
            self.assertAlmostEqual(b, c)

    def test_resaltado_sobrevive_al_partir(self):
        texto = marcar_por_palabra("Desaparecieron *300 personas* en una noche")
        self.assertIn("*300* *personas*", texto)
        frases = partir_frases(texto, 2, 40)
        self.assertTrue(all(f.count("*") % 2 == 0 for f in frases))
        self.assertEqual(frases[:2], ["Desaparecieron *300*", "*personas* en"])
        self.assertIn("{\\1c&H003FD2FF&}300{\\1c&H00FFFFFF&}", resaltar(frases[0], "&H003FD2FF"))
        self.assertEqual(sin_marcas("hola *mundo*"), "hola mundo")

    def test_limpiar(self):
        self.assertEqual(limpiar("a {b} c\\d\nlinea"), "a (b) c/d\\Nlinea")

    def test_documento(self):
        doc = Documento(1080, 1920)
        doc.gancho(0.1, 3, "Se dormían *sin aviso*")
        doc.dato(1, 4, "+100", "personas afectadas")
        doc.subtitulos(0.15, 2.5, "Caían dormidos en plena calle, en el trabajo o en clase.")
        doc.cierre(10, 13, "Cosas que pasan", "Suscríbete")
        txt = doc.contenido()
        self.assertIn("PlayResX: 1080", txt)
        self.assertIn("PlayResY: 1920", txt)
        self.assertIn("Style: Subtitulo,Poppins ExtraBold", txt)
        self.assertIn("Style: DatoValor,Anton", txt)
        self.assertEqual(txt.count(",DatoValor,,"), 1)
        self.assertIn("SE DORMÍAN", txt)
        self.assertGreaterEqual(txt.count(",Subtitulo,,"), 3)


if __name__ == "__main__":
    unittest.main()
