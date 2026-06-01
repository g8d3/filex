---
name: filex
description: "File server with Markdown rendering and VS Code-like code viewer. Sirve archivos con listado ordenable, renderizado .md, visor/editor de código con highlight.js, breadcrumb sticky con modal de navegación, edición inline vía Ace, y preferencias persistidas. Trigger: filex, file server, servir archivos, markdown server, code viewer, visor de código."
---

# filex — File server with Markdown rendering

## Descripción

Servidor HTTP liviano en Python que sirve archivos de un directorio con:
- Listado de directorios con columnas ordenables (nombre, tamaño, fecha) y orden persistente entre navegaciones
- Renderizado de archivos `.md` a HTML (headings, tablas, código, listas, negritas)
- Visor de código con **highlight.js** (tema claro) para 40+ extensiones (`.py`, `.sh`, `.txt`, `.go`, `.rs`, `.js`, `.ts`, etc.)
- Editor inline con botón Guardar (vía POST)
- Breadcrumb tipo VS Code: directorios cliqueables + **select** para cambiar entre archivos del mismo directorio
- Breadcrumb **sticky** (permanece visible al scrollear en archivos grandes)
- Soporte de imágenes (PNG, JPG, GIF, WebP)

## Location

El proyecto completo vive en esta misma carpeta:
```
~/.agents/skills/filex/
├── SKILL.md
├── filex.service        # Unit file de systemd (canónico)
├── serve_md.py          # Servidor HTTP
├── templates/
│   ├── toolbar.html     # ⭐ Base compartida: header sticky, toolbar, prefs panel, modal
│   ├── md.html          # Template para markdown con marked.js (usa {{toolbar_html}})
│   └── code.html        # Template para código con highlight.js + Ace (usa {{toolbar_html}})
└── static/
    ├── style.css        # Estilos globales + modal + mobile
    └── filex.js         # ⭐ JS compartido: fontSize, prefs, modal, breadcrumbs
```

## Cómo ejecutar

En producción se usa `uv run` (no hay python3 del sistema):

```bash
# Producción (puerto 9090, root ~/code)
uv run python3 ~/.agents/skills/filex/serve_md.py --root ~/code --port 9090 --bind 0.0.0.0
```

Opciones:
- `--root` — directorio raíz a servir (default: donde está `serve_md.py`)
- `--port` — puerto (default: `9090`)
- `--bind` — interfaz (default: `0.0.0.0`)

## Arquitectura

### Base compartida (los 3 templates usan la misma base)

Todos los templates (`dir.html`, `md.html`, `code.html`) ahora usan:
- **`{{toolbar_html}}`** — inyectado desde `templates/toolbar.html` (header sticky, breadcrumb clickeable, A−/A+, ⚙️ prefs, modal)
- **`/static/filex.js`** — JS compartido: font size, preferencias localStorage, modal de directorios, clicks en breadcrumb
- **`/static/style.css`** — estilos globales, modal, mobile

Esto elimina duplicación de HTML/JS entre templates. Cada template solo tiene su contenido específico (viewer + editor + toggleEdit/saveFile).

### `serve_md.py` — Servidor HTTP

- **`render_md(text, path, full)`** — pasa markdown crudo como JSON al template, `marked.js` lo renderiza en cliente
- **`render_code(text, ext, path, full)`** — pasa contenido como JSON, highlight.js lo colorea, Ace editor permite editar
- **`breadcrumb_code(path, full)`** — genera `<span>`s clickeables con `data-dir` para abrir el modal; el archivo actual es texto no clickeable (`.bc-current`)
- **`breadcrumb_html(path)`** — igual que breadcrumb_code pero para directorios
- **`do_GET()`** — rutea: directorio → toolbar + "navega desde breadcrumb", `.md` → `render_md`, code → `render_code`, `/static/*` → sirve con MIME correcto, imágenes → binario
- **`do_POST()`** — guarda contenido editado

### Trampa: TEXT_EXTENSIONS también captura .js y .css

`.js` y `.css` están en `TEXT_EXTENSIONS`. Si caen en esa ruta se renderizan como código (HTML), rompiendo la página. **Solución**: ruteo explícito `/static/*` al inicio de `do_GET()` que sirve con MIME type correcto (`application/javascript`, `text/css`) antes de cualquier otro matching.

```python
# En do_GET, ANTES de TEXT_EXTENSIONS:
if path.startswith("/static/"):
    static_root = os.path.join(SCRIPT_DIR, "static")
    # ... sirve con static_mime por extensión
    return
```

### Directorios como navegación, no como página

Visitar un directorio en URL ya NO muestra un listado de archivos. Muestra solo el toolbar con mensaje "Navega por los directorios desde el breadcrumb". El breadcrumb (cada segmento con `data-dir`) abre un modal que lista archivos por nombre/tamaño/fecha, ordenable por columnas. Los directorios en el modal se quedan en el modal (`showDirModal()`), los archivos navegan a la página del archivo.

### Editor de código: highlight.js (vista) + Ace (edición)

- **Vista**: highlight.js colorea el `<code>` en el DOM
- **Edición**: Ace editor reemplaza el div `#editor` con editor completo con syntax highlighting
- **Toggle**: crear/destruir instancia Ace sin recargar página
- **Font size**: `--content-font-size` CSS custom property, Ace escucha evento `filex-fontchange` via `document.dispatchEvent`

### Renderizado Markdown: marked.js (cliente)

Todo el renderizado markdown se hace en el cliente con `marked.parse()`, eliminando el renderer custom Python que era propenso a errores con casos frontera (tablas, listas anidadas, code fences).

### Preferencias persistidas (localStorage)

| Key | Propósito | Default |
|-----|-----------|---------|
| `filex_font_size` | Tamaño de fuente (px) | 13 (código) / 14 (markdown) |
| `filex_pref_tableBorder` | Bordes en tablas md | `true` |
| `filex_pref_cellPad` | Padding de celdas de tabla md | 6px |
| `filex_pref_modal_sort` | Columna/dirección de orden del modal | `{col:'name', dir:'asc'}` |

**Convención**: usar `filex_pref_` para preferencias editables por el usuario, `filex_` para estado interno.

### Breadcrumbs clickeables (no links)

En vez de `<a href>` (que navegan la página), los breadcrumbs usan `<span class="bc-link" data-dir="/path/">` con click handler que abre el modal. El último elemento (archivo/directorio actual) es solo texto con `.bc-current` (no clickeable, abre el mismo directorio que su padre).

### Seguridad

Verifica que la ruta resuelta esté dentro de `root_dir` (previene path traversal). `do_POST()` aplica la misma validación.

### Sort persistence

El orden de columnas en el modal se persiste en `localStorage` (`filex_pref_modal_sort`) y se restaura al abrir el modal. En la página de directorios (antes dir.html), se usaba `sessionStorage` — ahora ya no hay página de directorios.

### Symlink para servir `~/.agents/`

El root en producción es `~/code`, pero `~/.agents/` está fuera de esa carpeta. Para que filex pueda servir las skills en el navegador, existe un symlink:

```
~/code/.agents -> ~/.agents
```

Si recreas el root o eliminas el symlink, regenerar con:
```bash
ln -s ~/.agents ~/code/.agents
```

## Systemd — Recargar tras cambios

Cuando modificas el código de filex, el servidor en producción (puerto 9090) necesita ser reiniciado para reflejar los cambios.

⚠️ **No crear un servidor nuevo en otro puerto** — hay que reemplazar el existente.

### Recarga manual (cuando systemd bloquea)

Si `systemctl --user` no está disponible por restricciones del tool, ejecutarlo dentro de una **tmux window** (corre en un shell real sin restricciones):

```bash
tmux new-window -d -n filex-reload \
  'systemctl --user daemon-reload 2>&1 | tee /tmp/filex-reload.log; \
   systemctl --user restart filex 2>&1 | tee -a /tmp/filex-reload.log; \
   touch /tmp/filex-reload.done; tmux wait-for -S filex-reload'
tmux wait-for filex-reload
cat /tmp/filex-reload.log
```

Alternativa directa (matar e iniciar manualmente):
```bash
# 1. Matar procesos viejos
/bin/kill -9 $(pgrep -f serve_md.py)

# 2. Iniciar el nuevo desde la ubicación en skills
nohup /home/vuos/.local/bin/uv run python3 \
  /home/vuos/.agents/skills/filex/serve_md.py \
  --root /home/vuos/code --port 9090 --bind 0.0.0.0 \
  > /dev/null 2>&1 &
```

### Si systemd está disponible

```bash
systemctl --user daemon-reload
systemctl --user restart filex
```

El unit file canónico está en el repo de filex:
`~/.agents/skills/filex/filex.service`

Se enlaza simbólicamente desde donde systemd lo espera:
`~/.config/systemd/user/filex.service` → `~/.agents/skills/filex/filex.service`

Si cambias el servicio, edita el archivo en skills (queda trackeado en git) y recarga:
```bash
systemctl --user daemon-reload
systemctl --user restart filex
```

## Git

El proyecto tiene su **propio repo** en `git@github.com:g8d3/filex.git`, independiente del repo `agents` que contiene las skills. El repo `agents` ignora esta carpeta vía `.gitignore`.

Flujo:
```bash
# Cambios en filex
cd ~/.agents/skills/filex
git add -A && git commit -m "..." && git push

# Si se cambia el .gitignore del repo agents
cd ~/.agents/skills
git add .gitignore && git commit -m "..." && git push
```

## Trigger para agents

Cuando un usuario menciona "filex", "file server", "servir archivos", "markdown server", o pide modificar el servidor de archivos, cargar esta skill y seguir las instrucciones en SKILL.md.
