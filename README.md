# indexor

Framework para mantener un **índice curado de repositorios**: un `.md` con
tabla de contenidos y secciones, donde cada alta se pide por issue y se
publica sola cuando un aprobador la acepta. Sin dependencias: GitHub Actions
y Python de la librería estándar.

📖 El índice: [INDICE.md](INDICE.md)

## Cómo funciona

1. **Solicitar** — alguien abre un issue con el formulario «Alta en el
   índice» (nombre, URL, sección, descripción, responsable).
2. **Validar** — `indice-validar` revisa la solicitud y comenta el resultado:
   URL de un host permitido, sección existente, sin duplicados, largos
   máximos. Si se edita el issue, se vuelve a validar.
3. **Aprobar** — un aprobador pone la etiqueta **`aprobada`**.
4. **Publicar** — `indice-publicar` verifica que quien etiquetó esté
   autorizado, agrega la entrada a `datos/entradas.json`, regenera
   `INDICE.md`, hace el commit, cierra el issue y despliega el sitio en
   GitHub Pages.

Para rechazar una solicitud alcanza con cerrar el issue.

## Estructura

```
indice.config.json            Título, secciones, hosts permitidos, aprobadores
datos/entradas.json           Fuente de verdad del índice
INDICE.md                     Índice publicado (generado, no editar a mano)
tools/indice                  CLI (python3, sin dependencias)
tools/site/                   Assets del sitio de GitHub Pages
.github/ISSUE_TEMPLATE/       Formulario de alta (generado desde la config)
.github/workflows/            Validación, publicación, lint y sitio
```

## Adoptarlo en un repositorio nuevo

1. Crear el repositorio a partir de este (o copiar los archivos).
2. Editar `indice.config.json`: título, descripción, secciones y hosts.
3. Ejecutar `tools/indice build` y commitear. Esto regenera `INDICE.md` y el
   formulario de alta con las secciones nuevas.
4. En **Settings → Actions → General → Workflow permissions**, elegir
   **Read and write permissions**.
5. Las etiquetas (`alta`, `invalida`, `aprobada`, `publicada`) se crean solas
   con la primera solicitud.

## Quién puede aprobar

- Por defecto, quien tenga rol **Admin** o **Maintain** en el repositorio.
- Si `aprobadores` en `indice.config.json` tiene usuarios, **solo** ellos:
  `"aprobadores": ["Salterm27"]`.

Si alguien sin autorización pone la etiqueta, el workflow la quita y lo
avisa en el issue.

> **Rama principal**: el bot publica con un push directo a `main`. Un
> ruleset que exija pull request sobre `main` bloquea ese push, así que el
> control de este repositorio es la verificación del aprobador, no el
> ruleset. Quien tenga permiso de escritura puede igualmente editar los
> archivos a mano; conviene dar `Write` solo a quien corresponda (para abrir
> issues no hace falta).

## CLI

```bash
tools/indice build      # regenera INDICE.md y el formulario de alta
tools/indice lint       # valida config, entradas y archivos generados
tools/indice site       # genera el sitio en _site/
tools/indice add --nombre "Mi repo" --url https://github.com/org/repo \
  --seccion backend --descripcion "Qué hace"   # alta manual, sin issue
```

Para quitar o corregir una entrada, editar `datos/entradas.json` y ejecutar
`tools/indice build`.
