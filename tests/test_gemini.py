"""Prueba el cliente de Gemini con el SDK real, reemplazando solo la capa HTTP (sin red ni clave)."""

import base64
import importlib.util
import json
import math
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "cosas-que-pasan-2"
sys.path.insert(0, str(SKILL))

from cqp2 import medios  # noqa: E402
from cqp2.gemini import ErrorGemini, Gemini  # noqa: E402

try:
    medios.ffmpeg()
    DISPONIBLE = importlib.util.find_spec("google") is not None and importlib.util.find_spec("google.genai") is not None
except medios.ErrorMedios:
    DISPONIBLE = False

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def pcm_tono(segundos: float, frecuencia: int = 24000) -> bytes:
    silencio = b"\x00\x00" * int(0.4 * frecuencia)
    tono = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 220 * i / frecuencia)))
                    for i in range(int(segundos * frecuencia)))
    return silencio + tono + silencio


class Respuesta:
    def __init__(self, datos):
        self.body = json.dumps(datos)
        self.headers = {}


@unittest.skipUnless(DISPONIBLE, "requiere google-genai y ffmpeg")
class TestGemini(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.llamadas = []
        self.respuesta_contenido = None
        self.filtrado = False
        parches = [
            mock.patch.dict(os.environ, {"GEMINI_API_KEY": "falsa"}),
            mock.patch("google.genai._api_client.BaseApiClient.request", autospec=True, side_effect=self._request),
            mock.patch("google.genai._api_client.BaseApiClient.download_file", autospec=True, side_effect=self._descargar),
            mock.patch("cqp2.gemini.time.sleep"),
        ]
        for p in parches:
            p.start()
            self.addCleanup(p.stop)

    def _request(self, _cliente, metodo, ruta, cuerpo, http_options=None):
        self.llamadas.append((metodo, ruta, cuerpo))
        if ruta.endswith(":predictLongRunning"):
            return Respuesta({"name": "models/veo/operations/op1", "done": False})
        if metodo == "get":
            muestras = {"raiMediaFilteredCount": 1, "raiMediaFilteredReasons": ["personas reales"]} if self.filtrado else \
                {"generatedSamples": [{"video": {"uri": "https://generativelanguage.googleapis.com/v1beta/files/abc:download?alt=media"}}]}
            return Respuesta({"name": "models/veo/operations/op1", "done": True, "response": {"generateVideoResponse": muestras}})
        if ruta.endswith(":generateContent"):
            if self.respuesta_contenido is None:  # flujo completo: responde según el modelo
                if "tts" in ruta:
                    return Respuesta({"candidates": [{"content": {"role": "model", "parts": [{"inlineData": {
                        "mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(pcm_tono(0.8)).decode()}}]}}]})
                return Respuesta({"candidates": [{"content": {"role": "model", "parts": [{"inlineData": {
                    "mimeType": "image/png", "data": base64.b64encode(PNG).decode()}}]}}]})
            return Respuesta(self.respuesta_contenido)
        raise AssertionError(f"llamada inesperada {metodo} {ruta}")

    def _descargar(self, _cliente, ruta, *, http_options=None, destination=None):
        self.llamadas.append(("download", ruta, None))
        Path(destination).write_bytes(b"MP4")

    def test_video_con_imagen_inicial_y_referencias(self):
        ref = self.dir / "ref.png"
        ref.write_bytes(PNG)
        destino = self.dir / "e01.mp4"
        Gemini().video("a village", destino, modelo="veo-3.1-lite-generate-preview", aspecto="9:16",
                       resolucion="720p", duracion=6, evitar="text", imagen_inicial=ref, referencias=[ref])
        metodo, ruta, cuerpo = self.llamadas[0]
        self.assertEqual((metodo, ruta), ("post", "models/veo-3.1-lite-generate-preview:predictLongRunning"))
        instancia, parametros = cuerpo["instances"][0], cuerpo["parameters"]
        self.assertEqual(instancia["prompt"], "a village")
        self.assertEqual(instancia["image"]["mimeType"], "image/png")
        self.assertEqual(instancia["referenceImages"][0]["referenceType"], "ASSET")
        self.assertEqual(parametros, {"sampleCount": 1, "durationSeconds": 6, "aspectRatio": "9:16",
                                      "resolution": "720p", "negativePrompt": "text"})
        self.assertEqual(self.llamadas[-1][:2], ("download", "files/abc:download?alt=media"))
        self.assertEqual(destino.read_bytes(), b"MP4")

    def test_video_filtrado_explica_el_motivo(self):
        self.filtrado = True
        with self.assertRaises(ErrorGemini) as ctx:
            Gemini().video("x", self.dir / "e.mp4", modelo="veo", aspecto="16:9", resolucion="720p", duracion=4)
        self.assertIn("personas reales", str(ctx.exception))

    def test_imagen(self):
        self.respuesta_contenido = {"candidates": [{"content": {"role": "model", "parts": [
            {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(PNG).decode()}}]}}]}
        datos, mime = Gemini().imagen("an old sign", modelo="gemini-3.1-flash-image", aspecto="16:9")
        self.assertEqual((datos, mime), (PNG, "image/png"))
        cuerpo = self.llamadas[0][2]
        self.assertEqual(cuerpo["generationConfig"]["responseModalities"], ["IMAGE"])
        self.assertEqual(cuerpo["generationConfig"]["imageConfig"]["aspectRatio"], "16:9")

    def test_imagen_rechazada(self):
        self.respuesta_contenido = {"candidates": [{"content": {"role": "model", "parts": [{"text": "No puedo"}]}}]}
        with self.assertRaises(ErrorGemini) as ctx:
            Gemini().imagen("x", modelo="m", aspecto="1:1")
        self.assertIn("No puedo", str(ctx.exception))

    def test_voz_pcm_a_wav_sin_silencios(self):
        pcm = pcm_tono(1.0)
        self.respuesta_contenido = {"candidates": [{"content": {"role": "model", "parts": [
            {"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(pcm).decode()}}]}}]}
        destino = self.dir / "e01.wav"
        Gemini().voz("Hola mundo", destino, modelo="gemini-3.1-flash-tts-preview", voz="Charon",
                     indicaciones="Narra con calma.")
        cuerpo = self.llamadas[0][2]
        self.assertEqual(cuerpo["contents"][0]["parts"][0]["text"], "Narra con calma: Hola mundo")
        # el SDK envía speechConfig con nombres snake_case (la API acepta ambos estilos)
        self.assertIn('"Charon"', json.dumps(cuerpo["generationConfig"]["speechConfig"]))
        self.assertEqual(cuerpo["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertAlmostEqual(medios.duracion(destino), 1.1, delta=0.08)  # 1.8 s -> 1 s de voz + 0.05 s por lado
        self.assertFalse(destino.with_suffix(".crudo.wav").exists())

    def test_generar_con_api_y_no_pagar_dos_veces(self):
        from cqp2.guion import interpretar
        from cqp2.recursos import Modos, Recursos

        g = interpretar({"titulo": "t", "escenas": [
            {"id": "e01", "prompt": "a village", "narracion": "Un pueblo dormido.", "duracion": 4},
            {"id": "e02", "tipo": "imagen", "prompt": "a sign", "narracion": "Kalachi."},
        ]}, self.dir / "guion.json")
        r = Recursos(g, Modos())
        self.assertEqual(r.generar(confirmar=True, log=lambda *_: None), [])
        self.assertEqual(r.video(g.escena("e01")).read_bytes(), b"MP4")
        self.assertEqual(r.imagen(g.escena("e02")).suffix, ".png")
        self.assertTrue(r.voz(g.escena("e02")).exists())
        self.assertFalse(list((self.dir / "assets").rglob("*.parcial")))
        registro = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(x["tipo"] for x in registro["generados"]), ["imagen", "video", "voz", "voz"])
        self.assertGreater(registro["usd_estimado_total"], 0)

        antes = len(self.llamadas)
        self.assertEqual(r.estimar(), [])
        r.generar(log=lambda *_: None)  # todo en caché: ni pide confirmar ni llama a la API
        self.assertEqual(len(self.llamadas), antes)


if __name__ == "__main__":
    unittest.main()
