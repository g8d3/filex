# FileX — Guía rápida para agentes

## Stack
- Python puro (`http.server`), sin frameworks
- highlight.js (CDN) para syntax coloring
- Ace Editor (CDN) para edición
- marked.js (CDN) para renderizar Markdown

## Archivos clave
| Archivo | Rol |
|---|---|
| `serve_md.py` | Servidor HTTP + toda la lógica |
| `templates/code.html` | Template para archivos de código (highlight.js + Ace) |
| `templates/csv.html` | Template para archivos .csv (PapaParse → tabla HTML) |
| `templates/md.html` | Template para archivos .md (marked.js) |
| `templates/toolbar.html` | Toolbar compartido (breadcrumb, botones editar/guardar, modal directorios) |
| `templates/dir.html` | (no se usa activamente, la vista de directorio se genera inline) |
| `static/filex.js` | JS compartido (tamaño fuente, modal, preferencias) |
| `static/style.css` | Estilos |
| `filex.service` | systemd user service |

## Arquitectura del dispatch (`do_GET`)

El handler clasifica cada request en este orden:

1. **`/static/*`** → sirve archivos propios de filex (JS, CSS, imágenes) con MIME type fijo.
2. **Directorio** → si `?format=json` devuelve JSON para el modal; si no, HTML mínimo con toolbar.
3. **`.md`** → renderiza con `render_md()` (marked.js + editor texto plano).
4. **`.csv`** → renderiza con `render_csv()` (PapaParse → tabla HTML).
5. **`text_key in TEXT_EXTENSIONS`** → renderiza con `render_code()` (highlight.js + Ace editor).
6. **Extension multimedia** → sirve binario con MIME type (png, mp4, etc.).
7. **Fallback** → `application/octet-stream` (descarga).

## CSV rendering

`.csv` files get their own dispatch before the generic code path. The template `templates/csv.html` uses **PapaParse** CDN to parse CSV client-side into an HTML table with sticky headers, alternating row colors, and row count info.

Added extensions: `.csv`, `.log`.

## Los 3 diccionarios clave

### `TEXT_EXTENSIONS` (línea 31)
Set con extensiones que se renderizan como código. **Importante**: las claves pueden ser extensiones (`.py`, `.sh`) o nombres completos (`.gitignore`, `makefile`). La key se resuelve así:

```python
text_key = ext if ext else os.path.basename(full).lower()
```

Para agregar soporte para un nuevo tipo de archivo, añadirlo aquí + en `LANG_MAP`.

### `LANG_MAP` (línea 47)
Mapea `text_key` → lenguaje highlight.js. Usar `"plaintext"` si no hay syntax resaltado.

### `ACE_MODE_MAP` (línea 99)
Mapea lenguaje highlight.js → modo Ace editor. Usar `"text"` si no hay modo específico.

## Pitfalls comunes (lo que falló antes)

### 1. `os.path.splitext()` con dotfiles
```python
os.path.splitext(".gitignore")  # → (".gitignore", "") — EXTENSIÓN VACÍA
os.path.splitext(".env")        # → (".env", "")
os.path.splitext("Makefile")    # → ("Makefile", "")
```
El fix: si `ext` está vacío, usar `os.path.basename(full).lower()` como `text_key`.

### 2. `</script>` en el contenido
`json.dumps()` NO escapa `</script>`. Si el archivo contiene eso, rompe el HTML. Fix:
```python
safe_content = json.dumps(text).replace("</", "<\\/")
```

### 3. Clase `language-` para highlight.js
highlight.js espera `class="language-python"`, no `class="python"`. Fix en `render_code`:
```python
.replace("{{language}}", "language-" + lang)
```

## Edición (POST)
`do_POST` recibe `content` por form-urlencoded y escribe al archivo. No tiene autenticación ni backup — escribe directo.

## Service
```bash
systemctl --user restart filex
systemctl --user status filex
```
Corre en `http://localhost:9090/` sirviendo `~/code/`.

## Puerto
9090

## Workflow — hacer un cambio

1. **Editar el código** en `serve_md.py`, templates, o static.
2. **Verificar syntax**:
   ```bash
   python3 -c "import py_compile; py_compile.compile('serve_md.py', doraise=True)"
   ```
3. **Probar con curl** que los endpoints responden correctamente:
   ```bash
   # Código 200 + content-type text/html
   curl -s -o /dev/null -w "%{http_code} %{content_type}" http://localhost:9090/ruta/del/archivo
   # Verificar clase language- en el output
   curl -s http://localhost:9090/ruta/archivo.py | grep -o 'class="language-[^"]*"'
   ```
4. **Reiniciar service**:
   ```bash
   systemctl --user restart filex && sleep 1 && systemctl --user is-active filex
   ```
5. **Commit y push** (solo si el usuario lo pide explícitamente):
   ```bash
   cd ~/code/filex && git add -A && git commit -m "descripción del cambio" && git push
   ```
