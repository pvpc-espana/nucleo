# PVPC España · Núcleo de actualización

Aplicación web para consultar el **Precio Voluntario para el Pequeño Consumidor (PVPC)**
de la electricidad en España, hora a hora, para el día en curso y el día siguiente
(en cuanto se publica).

Referencia oficial: [MITECO · Precio voluntario para el pequeño consumidor](https://www.miteco.gob.es/es/energia/energia-electrica/electricidad/contratacion-suministro/precio-voluntario.html).

Este repositorio (`nucleo`) contiene el **proceso automático de obtención de datos**.
La documentación general del proyecto también vive aquí; el plan de implementación
por fases está en [`Plan.md`](Plan.md).

---

## 1. Descripción

El proyecto se divide en tres repositorios dentro de la organización `pvpc-espana`:

| Repositorio | Función | Publicación |
|-------------|---------|-------------|
| [`nucleo`](https://github.com/pvpc-espana/nucleo) | GitHub Action programada que consulta 4 veces al día la API pública de precios, normaliza los datos y los publica en `datos`. | — (sólo se ejecuta) |
| [`datos`](https://github.com/pvpc-espana/datos) | Almacén de datos estáticos (JSON) en `/docs`, servidos por GitHub Pages. | `https://datos.pvpc.linaresdigital.com` |
| [`frontal`](https://github.com/pvpc-espana/frontal) | Interfaz web (SPA) en Angular, compilada y publicada en GitHub Pages con GitHub Actions; lee los JSON de `datos` mediante `fetch`. | `https://pvpc.linaresdigital.com` |

No hay servidor propio ni base de datos: todo es contenido estático versionado en Git
y publicado con GitHub Pages. El histórico de precios queda registrado en el
historial de commits del repositorio `datos`.

## 2. Alcance

### Incluido (versión 1)

- Obtención automática del PVPC (término de energía activa, tarifa 2.0TD) para el
  **día en curso** y el **día siguiente** cuando ya esté publicado (habitualmente a
  partir de las ~20:15 hora peninsular).
- Ejecución programada **4 veces al día** y ejecución manual bajo demanda.
- Publicación en `datos` **sólo si hay cambios** (sin commits vacíos ni ruido).
- Formato JSON estable y versionado (`/v1/...`), un fichero por día más un índice.
- Interfaz web **mobile-first**:
  - Vista de un día con los precios por hora (gráfico de barras + lista).
  - Navegación al día anterior/siguiente **deslizando el dedo** (izquierda/derecha),
    con **botones en la parte superior e inferior** y con las flechas del teclado.
  - Los días sin precios muestran igualmente la rejilla de horas vacía para que el
    diseño no cambie.
  - Cambio de día **sin recargar la página** (SPA con URL enlazable por fecha).
  - Precio actual resaltado, mínimo, máximo y media del día.
  - Cada hora con **color e icono según umbrales de precio** (barata, media, cara,
    muy barata), como en el correo diario que ya genera el flujo de n8n (§3.8).
  - **Tema claro/oscuro** según el sistema operativo, con cambio manual (§3.8).
  - **Recordatorios**: marcar horas (o las más baratas) y añadirlas al calendario
    del dispositivo (`.ics`) o a Google Calendar, con aviso al comienzo de cada
    franja.
  - **Instalable como aplicación** (PWA) en móvil y escritorio, con funcionamiento
    sin conexión y aviso de nuevas versiones. En Android ocupa menos de 1 MB
    (detalle en el [README de `frontal`](https://github.com/pvpc-espana/frontal#espacio-que-ocupa-instalada-en-android)).
- Interfaz en **6 idiomas**: castellano (por defecto), inglés, francés, alemán,
  italiano y portugués, con formato de números, fechas y moneda según el idioma.
- Horas expresadas en **hora peninsular** (`Europe/Madrid`), contemplando los días de
  cambio de horario (23 y 25 horas).

### Fuera de alcance (posibles ampliaciones)

- Precios de Ceuta y Melilla (serie PVPC propia) y visualización en hora canaria.
- Términos de potencia, peajes desglosados, simulación de factura.
- Notificaciones push / alertas de precio (Web Push con un servicio externo).
- Comparativas históricas (semanal, mensual, anual).
- Cuentas de usuario o cualquier dato personal.

## 3. Arquitectura

```
                 4 veces al día (cron) / manual
                              │
                              ▼
┌──────────────────────────────────────────────────────┐
│  nucleo  (GitHub Actions)                            │
│  1. Determina fechas a consultar (hoy, mañana)       │
│  2. Consulta e·sios (secreto TESTIGO)                │
│  3. Valida y normaliza → JSON v1                     │
│  4. Clona `datos` con clave de despliegue (SSH)      │
│  5. Escribe ficheros; commit + push sólo si cambian  │
└──────────────────────────────────────────────────────┘
          │ API e·sios (HTTPS)            │ git push (deploy key, escritura)
          ▼                               ▼
  api.esios.ree.es            ┌────────────────────────────────┐
                              │ datos  (GitHub Pages, /docs)   │
                              │ datos.pvpc.linaresdigital.com  │
                              └────────────────────────────────┘
                                          ▲ fetch (CORS: GitHub Pages
                                          │ responde con ACAO *)
                              ┌────────────────────────────────┐
                              │ frontal (GitHub Pages, Actions)│
                              │ pvpc.linaresdigital.com        │
                              │ Angular SPA, 6 idiomas         │
                              └────────────────────────────────┘
                                          ▲
                                          │ navegador (móvil primero)
                                       Usuario
```

### 3.1 Fuente de datos

- **Principal:** API de e·sios (REE), indicador **`1001`** (PVPC 2.0TD), autenticada
  con un *token* personal guardado como secreto de Actions **`TESTIGO`**:
  `https://api.esios.ree.es/indicators/1001?start_date=…&end_date=…&geo_ids[]=8741`
  con las cabeceras `Accept: application/json; application/vnd.esios-api-v1+json` y
  `x-api-key: <TESTIGO>`. Permite obtener el día siguiente en cuanto se publica y
  también días pasados (carga histórica). De la respuesta se toman los valores de la
  zona peninsular (`geo_id` 8741), que aplican también a Baleares y Canarias.
- `start_date` y `end_date` se calculan como **medianoche en `Europe/Madrid`** del
  día pedido y del siguiente, con su desfase horario explícito
  (p. ej. `2026-10-25T00:00:00+02:00` → `2026-10-26T00:00:00+01:00`). Calcularlas
  en UTC desplaza el día y pierde horas: es lo que le ocurre al flujo actual de
  n8n, que usa `setHours(0)` en un servidor en UTC.
- **Respaldo (sin autenticación):** API pública `apidatos.ree.es`
  (`/es/datos/mercados/precios-mercados-tiempo-real?...&time_trunc=hour`), serie
  PVPC; sólo se usa si e·sios falla.
- El *token* nunca se escribe en los registros ni en los ficheros publicados.
- Los valores llegan en €/MWh y se publican convertidos a **€/kWh** con 5 decimales.
- Desde octubre de 2025 el mercado diario opera en periodos **cuartohorarios**. El
  formato de datos incluye el campo `resolucion` y una lista de periodos de longitud
  variable para soportar tanto 24 (±1) horas como 96 (±4) cuartos de hora; la fase 1
  del plan valida qué granularidad entrega realmente la API para el PVPC.

### 3.2 Programación del núcleo

Los precios del día siguiente se publican a partir de las **20:00** (hora
peninsular) y se recomienda esperar unos minutos. Las ejecuciones deseadas, en hora
`Europe/Madrid`, son:

| Hora peninsular | Cron invierno (CET, UTC+1) | Cron verano (CEST, UTC+2) | Objetivo |
|---|---|---|---|
| 07:00 | `0 6 * * *`   | `0 5 * * *`   | Confirmar que están los precios del día en curso. |
| 20:10 | `10 19 * * *` | `10 18 * * *` | Primer intento de obtener el día siguiente. |
| 21:00 | `0 20 * * *`  | `0 19 * * *`  | Reintento del día siguiente. |
| 23:30 | `30 22 * * *` | `30 21 * * *` | Último reintento del día siguiente (y alerta si falta). |

GitHub Actions sólo admite `cron` en **UTC**, así que el workflow declara los 8
cron y su primer paso compara `github.event.schedule` (la expresión que lo ha
disparado) con el desfase horario actual de `Europe/Madrid`: si el cron no es el
de la estación vigente, el trabajo termina sin hacer nada. Así se ejecuta
exactamente 4 veces al día todo el año, aunque GitHub retrase la ejecución
(los retrasos de varios minutos son habituales, sobre todo en horas en punto).

En cada ejecución se consultan **hoy y mañana** (hora `Europe/Madrid`): así la de
las 07:00 confirma el día en curso y las de la tarde-noche obtienen el siguiente y
detectan correcciones del actual. Si mañana aún no está publicado, se ignora sin
error. Se añade `workflow_dispatch` (con fecha o rango opcional) para ejecuciones
manuales y recargas históricas.

> GitHub desactiva los workflows programados de un repositorio público tras 60 días
> sin actividad en él. Como los commits se hacen en `datos` y no en `nucleo`, se
> incluye un mecanismo de mantenimiento (ver Fase 2 del plan).

### 3.3 Publicación en `datos` y clave de despliegue

1. Se genera un par de claves SSH **exclusivo** para este uso:
   ```bash
   ssh-keygen -t ed25519 -C "nucleo→datos" -N "" -f datos_deploy_key
   ```
2. En `datos` → *Settings → Deploy keys* se añade `datos_deploy_key.pub` con
   **Allow write access**.
3. En `nucleo` → *Settings → Secrets and variables → Actions* se crea el secreto
   `DATOS_DEPLOY_KEY` con el contenido de la clave privada `datos_deploy_key`.
4. Se borran las claves locales.

El workflow clona `datos` con `actions/checkout` (`repository: pvpc-espana/datos`,
`ssh-key: ${{ secrets.DATOS_DEPLOY_KEY }}`), regenera los ficheros y ejecuta
`git status --porcelain`; **sólo si hay diferencias** hace commit y push. Los
ficheros no incluyen la hora de ejecución (salvo el índice, que sólo se reescribe
cuando cambia algún día), de modo que una ejecución sin datos nuevos no genera cambios.

### 3.4 Formato de datos (`datos/docs`)

```
docs/
├── CNAME                     # datos.pvpc.linaresdigital.com
├── .nojekyll
├── index.html                # página informativa mínima
└── v1/
    ├── indice.json           # rango de fechas disponible y última actualización
    └── AAAA/MM/AAAA-MM-DD.json
```

Fichero diario (`v1/2026/10/2026-10-25.json`, día de 25 horas):

```json
{
  "fecha": "2026-10-25",
  "zona": "peninsula",
  "unidad": "EUR/kWh",
  "resolucion": "PT1H",
  "fuente": "REE",
  "resumen": { "min": 0.08123, "max": 0.21456, "media": 0.13789 },
  "precios": [
    { "inicio": "2026-10-25T00:00:00+02:00", "precio": 0.12345 },
    { "inicio": "2026-10-25T01:00:00+02:00", "precio": 0.11876 },
    { "inicio": "2026-10-25T02:00:00+02:00", "precio": 0.11002 },
    { "inicio": "2026-10-25T02:00:00+01:00", "precio": 0.10950 }
  ]
}
```

`indice.json`:

```json
{ "version": 1, "primera": "2026-01-01", "ultima": "2026-10-25", "actualizado": "2026-10-24T19:41:12Z" }
```

El `inicio` de cada periodo lleva el desfase horario explícito para resolver sin
ambigüedad los días de cambio de hora. GitHub Pages sirve los ficheros con
`Access-Control-Allow-Origin: *`, por lo que el frontal puede leerlos desde otro
subdominio.

### 3.5 Frontal

- **SPA en Angular** con componentes *standalone* y *signals*; el día seleccionado
  forma parte de la URL (`/es/2026-10-24`), de modo que cada día es enlazable y el
  cambio de día no recarga la página.
- **Servicio de datos** con caché en memoria y **precarga** del día anterior y
  siguiente para que el deslizamiento sea instantáneo. Un 404 en un día se trata
  como «sin precios» (se pintan las horas vacías).
- **Gestos**: directiva propia basada en *Pointer Events* (umbral de distancia y
  velocidad, sin dependencias), animación de transición y respeto de
  `prefers-reduced-motion`.
- **Internacionalización** en tiempo de ejecución (Transloco) con los 6 idiomas,
  detección por `navigator.language`, selector manual persistido y formato
  numérico/fechas con `Intl`. Permite cambiar de idioma sin recargar y mantener un
  único *build*.
- **Publicación con GitHub Actions** (workflow `publicar.yml`): en cada push a
  `main` se ejecutan formato y tests, se compila con `npm run build` (`ng build`
  con `outputPath: { base: "dist", browser: "" }` seguido de
  `scripts/paginas-entrada.mjs`, que genera `404.html`, las páginas de entrada por
  idioma y la CSP) y se despliega con
  `actions/upload-pages-artifact` + `actions/deploy-pages`. El código compilado no
  se guarda en Git y el dominio propio se configura en *Settings → Pages* (con
  este método GitHub ignora el fichero `CNAME`).
- **Rutas con `/` (no `#`)** sobre GitHub Pages; ver §3.7.
- **Temas y clasificación visual de precios**; ver §3.8.

### 3.6 ¿Por qué dos métodos de publicación?

- **`datos` publica desde la rama (`main`, carpeta `/docs`)**: los JSON ya los
  versiona el núcleo y no hay nada que compilar; cada push se publica solo, sin
  workflow propio, y `.nojekyll` evita el procesado de Jekyll.
- **`frontal` publica con GitHub Actions**: necesita Node para compilar; así no se
  versionan ficheros generados (con *hash* en el nombre, que ensuciarían el
  historial y provocarían conflictos) y sólo se publica lo que pasa las pruebas.

### 3.7 Rutas en GitHub Pages: limitaciones y soluciones

Se usan rutas basadas en `/` (`PathLocationStrategy`) en lugar de `#`: URLs limpias
e indexables. GitHub Pages sólo sirve ficheros existentes, así que una ruta como
`/es/2026-10-24` se resuelve con `404.html` (copia de `index.html`): Angular arranca
y el router muestra el día pedido. Limitaciones y cómo se resuelven:

| Limitación | Solución adoptada |
|---|---|
| Las rutas profundas responden con estado HTTP **404** aunque la página funcione (buscadores, vistas previas y monitores pueden tratarlas como error). | Tras `ng build`, el script `scripts/paginas-entrada.mjs` genera ficheros reales para `/` y `/{es,en,fr,de,it,pt}/index.html` a partir de `index.html`, con su `lang`, `<title>`, descripción, Open Graph y `hreflang` tomados de los ficheros de traducción, de modo que las páginas de entrada responden **200**. Las URLs con fecha siguen resolviéndose por `404.html` (son vistas efímeras sin valor para indexar). |
| Las vistas previas al compartir (WhatsApp, Telegram…) no ejecutan JavaScript. | Metadatos Open Graph completos y genéricos en `index.html`, y específicos por idioma en las páginas de entrada. |
| No se pueden definir cabeceras HTTP ni redirecciones de servidor (la caché la fija GitHub en ~10 min). | CSP mediante `<meta http-equiv="Content-Security-Policy">`; redirecciones (`/` → `/<idioma>/`, rutas desconocidas) en el router de Angular. |
| Tras un despliegue, quien tenga la app abierta conserva un `index.html` que apunta a ficheros con *hash* ya inexistentes (`ChunkLoadError` en módulos de carga diferida). | Pocos módulos de carga diferida y un manejador de errores de navegación que, ante un fallo de carga de módulo, recarga la página una sola vez. |
| Las rutas relativas fallarían dentro de una subruta (`/es/2026-10-24/assets/...`). | `<base href="/">` y recursos (traducciones, iconos) con rutas absolutas; el sitio vive en la raíz del dominio. |

Otros límites de GitHub Pages (1 GB por sitio, ~100 GB de tráfico mensual
orientativo) quedan muy por encima del uso previsto.

### 3.8 Temas y clasificación visual de precios

**Temas**

- Tres modos: **Automático** (por defecto, sigue `prefers-color-scheme` del sistema
  y reacciona en vivo si el sistema cambia), **Claro** y **Oscuro**, elegibles con
  un selector en la cabecera. La elección se guarda en `localStorage`.
- Implementación con variables CSS (*design tokens*) en `:root` y el atributo
  `data-tema="claro|oscuro"` en `<html>`; `color-scheme` y
  `<meta name="theme-color">` se actualizan para que barras del navegador,
  controles nativos y barras de desplazamiento sigan el tema.
- Para evitar el destello del tema equivocado al cargar, un pequeño script en línea
  en `<head>` aplica el tema guardado antes de que arranque Angular (su *hash* se
  incluye en la CSP de `index.html`).
- Los colores de los tramos tienen una variante por tema para mantener contraste
  WCAG AA (p. ej. el naranja sobre blanco necesita un tono más oscuro que sobre
  fondo oscuro).

**Clasificación de cada hora** (basada en el correo diario de n8n)

Cada hora combina un **color** (tramo) y un **icono**:

Ambos dependen de la posición relativa del precio dentro del rango del día,
`r = (precio − mín) / (máx − mín)` (si `máx = mín`, `r = 0`), con los mismos
umbrales que el flujo de n8n:

| Color | Regla | | Icono | Regla |
|---|---|---|---|---|
| Verde (barata) | `r ≤ 0,33` | | ✅ (de las más baratas) | `r < 0,15` |
| Naranja (media) | `0,33 < r ≤ 0,66` | | 🔘 (normal) | `0,15 ≤ r ≤ 0,85` |
| Rojo (cara) | `r > 0,66` | | ⚠️ (de las más caras) | `r > 0,85` |

Color e icono son independientes (p. ej. una hora con `r = 0,25` es verde con 🔘, y
una con `r = 0,75` es roja con 🔘). Los umbrales viven en un único fichero de
configuración del frontal (`umbrales.ts`) para poder ajustarlos sin tocar los
componentes.

- En la web los iconos se dibujan como SVG propios (aspecto idéntico en todos los
  sistemas, a diferencia de los emojis) y llevan texto accesible traducido
  («muy barata», «cara»…); la información nunca depende sólo del color.
- El color se aplica a la barra del gráfico y a la fila de la lista; el resumen
  del día muestra el mínimo y el máximo con su icono.

> El correo de ejemplo corresponde al 25/10/2026, día de **25 horas** por el cambio
> al horario de invierno, y sólo lista de 02:00 a 23:00 (faltan 00:00, 01:00 y la
> repetición de 02:00) porque el flujo de n8n calcula el rango de fechas en UTC
> (§3.1). La web debe mostrar siempre todas las horas del día (§3.4: `inicio` con
> desfase horario explícito).

## 4. Tecnologías

| Ámbito | Tecnología |
|--------|-----------|
| Núcleo | Python 3.12+ (biblioteca estándar: `urllib`, `json`, `zoneinfo`), `pytest`, `ruff` |
| Automatización | GitHub Actions (`schedule`, `workflow_dispatch`, `concurrency`) |
| Acceso a `datos` | Clave de despliegue SSH ed25519 con permiso de escritura + secreto de Actions |
| Fuente de datos | API e·sios de REE, indicador 1001, con secreto `TESTIGO`; `apidatos.ree.es` como respaldo |
| Alojamiento | GitHub Pages con dominio propio y HTTPS: `datos` desde rama (`main`, `/docs`); `frontal` desde GitHub Actions |
| DNS | Registros `CNAME` de `pvpc` y `datos.pvpc` hacia `pvpc-espana.github.io` |
| Frontal | Angular 22 (sin zone.js), TypeScript, SCSS, Transloco, `Intl`, fuente Inter |
| Gráficos | Barras con CSS Grid generadas por el propio componente (sin librería de gráficos) |
| Pruebas frontal | Vitest (unitarias); Playwright (extremo a extremo, emulación móvil) previsto en la fase 7 |
| Calidad | ESLint, Prettier, Lighthouse (rendimiento y accesibilidad) |

## 5. Estructura prevista de este repositorio

```
nucleo/
├── .github/workflows/
│   ├── actualizar.yml        # cron ×4 + manual: obtiene y publica precios
│   └── pruebas.yml           # lint + tests en cada push/PR
├── pvpc/
│   ├── fuente_esios.py       # cliente de e·sios (secreto TESTIGO)
│   ├── fuente_ree.py         # cliente de respaldo (apidatos.ree.es)
│   ├── normalizar.py         # validación y conversión al formato v1
│   ├── publicar.py           # escritura de ficheros e índice
│   └── __main__.py           # CLI: python -m pvpc --salida ../datos/docs [--fecha …]
├── tests/
├── README.md
├── Plan.md
└── LICENSE                   # GPL-3.0
```

## 6. Licencia

GPL-3.0. Los datos de precios proceden de Red Eléctrica de España y se publican
según sus condiciones de uso.

## Agradecimientos

Gracias a [Claude](https://claude.ai), de [Anthropic](https://www.anthropic.com), por su
inestimable ayuda en la creación y depuración de este proyecto.
