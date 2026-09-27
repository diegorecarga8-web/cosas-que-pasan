"""Cliente de la API de Gemini (google-genai) para Veo, imágenes y voz.

La clave se lee de GEMINI_API_KEY (o GOOGLE_API_KEY). Ver referencia/configurar-gemini.md.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from . import medios


class ErrorGemini(RuntimeError):
    pass


class Gemini:
    def __init__(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ErrorGemini("Falta el paquete google-genai: pip install -r requirements.txt") from exc
        self.types = types
        reintentos = types.HttpRetryOptions(attempts=5, initial_delay=5.0, max_delay=60.0,
                                            http_status_codes=[429, 500, 502, 503, 504])
        self.client = genai.Client(http_options=types.HttpOptions(retry_options=reintentos))
        self._sin_afc = types.AutomaticFunctionCallingConfig(disable=True)  # no usamos herramientas

    def video(self, prompt: str, destino: Path, *, modelo: str, aspecto: str, resolucion: str, duracion: int,
              evitar: str = "", imagen_inicial: Path | None = None, referencias: list[Path] | None = None,
              espera: float = 10.0, limite: float = 1200.0) -> None:
        t = self.types
        config = t.GenerateVideosConfig(
            aspect_ratio=aspecto,
            resolution=resolucion,
            duration_seconds=duracion,
            number_of_videos=1,
            negative_prompt=evitar or None,
            reference_images=[t.VideoGenerationReferenceImage(image=t.Image.from_file(location=str(r)), reference_type="ASSET")
                              for r in referencias] if referencias else None,
        )
        fuente = t.GenerateVideosSource(
            prompt=prompt,
            image=t.Image.from_file(location=str(imagen_inicial)) if imagen_inicial else None,
        )
        operacion = self.client.models.generate_videos(model=modelo, source=fuente, config=config)
        inicio = time.time()
        while not operacion.done:
            if time.time() - inicio > limite:
                raise ErrorGemini(f"Veo tardó más de {limite / 60:.0f} min (operación {operacion.name})")
            time.sleep(espera)
            operacion = self.client.operations.get(operacion)
        if operacion.error:
            raise ErrorGemini(f"Veo devolvió un error: {operacion.error}")
        respuesta = operacion.response or operacion.result
        videos = respuesta.generated_videos if respuesta else None
        if not videos or not videos[0].video:
            razones = "; ".join(respuesta.rai_media_filtered_reasons or []) if respuesta else ""
            raise ErrorGemini("Veo no devolvió video (probablemente lo bloqueó el filtro de seguridad). "
                              f"Reformula el prompt. {razones}".strip())
        self.client.files.download(file=videos[0].video, destination=str(destino))
        if not destino.exists() or destino.stat().st_size == 0:
            raise ErrorGemini("La descarga del video quedó vacía")

    def imagen(self, prompt: str, *, modelo: str, aspecto: str) -> tuple[bytes, str]:
        t = self.types
        respuesta = self.client.models.generate_content(
            model=modelo,
            contents=[prompt],
            config=t.GenerateContentConfig(response_modalities=["IMAGE"], image_config=t.ImageConfig(aspect_ratio=aspecto),
                                           automatic_function_calling=self._sin_afc),
        )
        textos = []
        for candidato in respuesta.candidates or []:
            for parte in (candidato.content.parts if candidato.content else None) or []:
                if parte.inline_data and parte.inline_data.data:
                    return parte.inline_data.data, parte.inline_data.mime_type or "image/png"
                if parte.text:
                    textos.append(parte.text)
        raise ErrorGemini("El modelo de imagen no devolvió imagen. " + " ".join(textos)[:300])

    def voz(self, texto: str, destino: Path, *, modelo: str, voz: str, indicaciones: str = "") -> None:
        from .recursos import escribir_wav

        t = self.types
        contenido = f"{indicaciones.rstrip(' .:')}: {texto}" if indicaciones else texto
        respuesta = self.client.models.generate_content(
            model=modelo,
            contents=contenido,
            config=t.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=t.SpeechConfig(voice_config=t.VoiceConfig(
                    prebuilt_voice_config=t.PrebuiltVoiceConfig(voice_name=voz))),
                automatic_function_calling=self._sin_afc,
            ),
        )
        parte = None
        for candidato in respuesta.candidates or []:
            for p in (candidato.content.parts if candidato.content else None) or []:
                if p.inline_data and p.inline_data.data:
                    parte = p
                    break
        if parte is None:
            raise ErrorGemini("El modelo de voz no devolvió audio")
        mime = (parte.inline_data.mime_type or "").lower()
        crudo = destino.with_suffix(".crudo.wav")
        if "wav" in mime:
            crudo.write_bytes(parte.inline_data.data)
        else:  # PCM de 16 bits, normalmente "audio/L16;codec=pcm;rate=24000"
            m = re.search(r"rate=(\d+)", mime)
            escribir_wav(crudo, parte.inline_data.data, frecuencia=int(m.group(1)) if m else 24000)
        recortar_silencios(crudo, destino)
        crudo.unlink(missing_ok=True)


def recortar_silencios(origen: Path, destino: Path) -> None:
    """Quita el silencio del principio y del final para que los subtítulos queden sincronizados."""
    quitar = "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB"
    medios.ejecutar(["-i", str(origen), "-af", f"{quitar},areverse,{quitar},areverse", str(destino)],
                    descripcion="recorte de silencios de la voz")
