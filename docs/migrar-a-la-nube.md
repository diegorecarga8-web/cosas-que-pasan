# Cómo migrar el proyecto para que no dependa de tu PC

Sigue estos pasos **desde la sesión local** que tiene el skill, los scripts y las
imágenes (*"Cosas que pasan"* o *"Eficiencia: imágenes vs animación en Cosas que
pasan"*), cuando esté disponible de nuevo (después del reset del límite de uso).

## 1. Verifica que el proyecto local esté conectado a este repo

```bash
git remote -v
```

Si no aparece `https://github.com/diegorecarga8-web/cosas-que-pasan`, agrégalo:

```bash
git remote add origin https://github.com/diegorecarga8-web/cosas-que-pasan
```

Si ya existe un remoto distinto, dime cuál es antes de sobreescribirlo.

## 2. Revisa qué se va a subir

- **Incluye:** el skill (`.claude/skills/...`), los scripts de descarga/render, las
  imágenes, fuentes y sonidos que usa el pipeline, la configuración de efectos ya
  afinada.
- **Excluye** (vía `.gitignore`): renders de prueba pesados que no necesitas
  versionar (por ejemplo los que ya marcas como `NO_SUBIR`), carpetas temporales,
  cachés, `node_modules`, etc.

Ejemplo de `.gitignore` de partida:

```gitignore
*_NO_SUBIR.*
/tmp/
/.cache/
node_modules/
*.log
```

## 3. Si las imágenes/videos pesan mucho

Con 105 imágenes (y potencialmente varios renders de video), el repo puede crecer
rápido. Si el total pasa de unos cientos de MB, usa Git LFS para las imágenes y
videos en vez de subirlos como archivos normales:

```bash
git lfs install
git lfs track "*.png" "*.jpg" "*.jpeg" "*.mp4"
git add .gitattributes
```

## 4. Commit y push

```bash
git add .
git commit -m "Migrar pipeline de generación de video a la nube"
git push -u origin claude/great-dirac-c6dlqi
```

(Usa esa rama, que es la que esta sesión en la nube ya tiene configurada para este
repo; si prefieres otra rama o `main`, también funciona — solo dímelo para ajustar
por dónde continuar en la nube.)

## 5. Ya en la nube

Una vez pusheado, cualquier sesión de Claude Code en la nube que apunte a este repo
y esa rama tendrá el skill, los scripts y las imágenes disponibles, y podrá seguir
generando video sin que tu PC esté encendido ni conectado.

Lo único que sigue igual: el límite de uso de la cuenta (ventana de 5 horas) es
compartido entre todas las sesiones, sin importar dónde corran.
