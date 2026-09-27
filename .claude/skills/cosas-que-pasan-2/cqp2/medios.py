"""Utilidades de ffmpeg: localizar el binario, ejecutar comandos y leer duraciones."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

DIR_SKILL = Path(__file__).resolve().parent.parent
DIR_FUENTES = DIR_SKILL / "fuentes"


class ErrorMedios(RuntimeError):
    pass


@lru_cache(maxsize=1)
def ffmpeg() -> str:
    """Ruta a ffmpeg: variable CQP2_FFMPEG, luego el binario de imageio-ffmpeg y por último el PATH.

    Se prefiere imageio-ffmpeg porque trae libass (subtítulos con estilo) en todas las plataformas.
    """
    propio = os.environ.get("CQP2_FFMPEG")
    if propio:
        return propio
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    en_path = shutil.which("ffmpeg")
    if en_path:
        return en_path
    raise ErrorMedios(
        "No encontré ffmpeg. Instala las dependencias con:\n"
        "  pip install -r .claude/skills/cosas-que-pasan-2/requirements.txt"
    )


def ejecutar(args: list[str], cwd: Path | None = None, descripcion: str = "ffmpeg") -> None:
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        detalle = (proc.stderr or proc.stdout).strip()[-3000:]
        raise ErrorMedios(f"Falló {descripcion} (código {proc.returncode}):\n{detalle}")


def _info(ruta: Path) -> str:
    cmd = [ffmpeg(), "-hide_banner", "-i", str(ruta)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stderr


def duracion(ruta: Path) -> float:
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", _info(ruta))
    if not m:
        raise ErrorMedios(f"No pude leer la duración de {ruta}")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def tiene_audio(ruta: Path) -> bool:
    return bool(re.search(r"Stream #\d+:\d+.*: Audio:", _info(ruta)))


def dimensiones(ruta: Path) -> tuple[int, int]:
    m = re.search(r"Stream #\d+:\d+.*: Video:.*?[, ](\d{2,5})x(\d{2,5})[, \[]", _info(ruta))
    if not m:
        raise ErrorMedios(f"No pude leer las dimensiones de {ruta}")
    return int(m.group(1)), int(m.group(2))


def preparar_fuentes(destino: Path) -> str:
    """Copia las fuentes junto a los archivos de render y devuelve el nombre relativo para `fontsdir`.

    Así los filtros de ffmpeg solo reciben nombres simples y no hay que escapar rutas de Windows.
    """
    carpeta = destino / "fuentes"
    carpeta.mkdir(parents=True, exist_ok=True)
    for f in DIR_FUENTES.glob("*.ttf"):
        objetivo = carpeta / f.name
        if not objetivo.exists() or objetivo.stat().st_size != f.stat().st_size:
            shutil.copy2(f, objetivo)
    return "fuentes"
