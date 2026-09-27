#!/bin/bash
# Instala las dependencias de Cosas que pasan 2 (google-genai, imageio-ffmpeg) en las sesiones
# de Claude Code en la web. En el PC no hace nada: ahí se instalan una vez con pip.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore \
  -r .claude/skills/cosas-que-pasan-2/requirements.txt
