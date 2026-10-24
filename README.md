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
| [`datos`](https://github.com/pvpc-espana/datos) | Almacén de datos estáticos (JSON) en `/docs`, servidos por GitHub Pages. | `https://datos.pvcp.linaresdigital.com` |
| [`frontal`](https://github.com/pvpc-espana/frontal) | Interfaz web (SPA) compilada en `/docs`, servida por GitHub Pages, que lee los JSON de `datos` mediante `fetch`. | `https://pvcp.linaresdigital.com` |

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
  - Precio actual resaltado, mínimo, máximo y media del día, y franjas
    baratas/medias/caras.
- Interfaz en **6 idiomas**: castellano (por defecto), inglés, francés, alemán,
  italiano y portugués, con formato de números, fechas y moneda según el idioma.
- Horas expresadas en **hora peninsular** (`Europe/Madrid`), contemplando los días de
  cambio de horario (23 y 25 horas).

### Fuera de alcance (posibles ampliaciones)

- Precios de Ceuta y Melilla (serie PVPC propia) y visualización en hora canaria.
- Términos de potencia, peajes desglosados, simulación de factura.
- Notificaciones push / alertas de precio, PWA instalable con modo sin conexión.
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
                              │ datos.pvcp.linaresdigital.com  │
                              └────────────────────────────────┘
                                          ▲ fetch (CORS: GitHub Pages
                                          │ responde con ACAO *)
                              ┌────────────────────────────────┐
                              │ frontal (GitHub Pages, /docs)  │
                              │ pvcp.linaresdigital.com        │
                              │ Angular SPA, 6 idiomas         │
                              └────────────────────────────────┘
                                          ▲
                                          │ navegador (móvil primero)
                                       Usuario
```

### 3.1 Fuente de datos

- **Principal:** API de e·sios (REE), indicador **`1001`** (PVPC 2.0TD), autenticada
  con un *token* personal guardado como secreto de Actions **`TESTIGO`**:
  `https://api.esios.ree.es/indicators/1001?start_date=AAAA-MM-DDT00:00&end_date=AAAA-MM-DDT23:59`
  con las cabeceras `Accept: application/json; application/vnd.esios-api-v1+json` y
  `x-api-key: <TESTIGO>`. Permite obtener el día siguiente en cuanto se publica y
  también días pasados (carga histórica). De la respuesta se toman los valores de la
  zona peninsular (`geo_id` 8741), que aplican también a Baleares y Canarias.
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

GitHub Actions usa `cron` en **UTC**. Se proponen estas ejecuciones:

| Cron (UTC) | Invierno (UTC+1) | Verano (UTC+2) | Objetivo |
|-----------|------------------|----------------|----------|
| `7 0 * * *`  | 01:07 | 02:07 | Confirmar el día en curso (recién empezado). |
| `7 10 * * *` | 11:07 | 12:07 | Detectar correcciones del día en curso. |
| `37 19 * * *` | 20:37 | 21:37 | Obtener el día siguiente (publicado ~20:15). |
| `37 21 * * *` | 22:37 | 23:37 | Reintento del día siguiente si la anterior no lo obtuvo. |

En cada ejecución se consultan **hoy y mañana** (hora `Europe/Madrid`); si mañana aún
no está publicado, se ignora sin error. Los minutos no son en punto para evitar la
congestión de las colas de GitHub. Se añade `workflow_dispatch` (con fecha opcional)
para ejecuciones manuales y recargas históricas.

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
├── CNAME                     # datos.pvcp.linaresdigital.com
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
- **Compilación a `/docs`** (`outputPath: { base: "docs", browser: "" }`), con
  `CNAME`, `.nojekyll` y `404.html` (copia de `index.html`) para que las rutas
  profundas funcionen en GitHub Pages.

## 4. Tecnologías

| Ámbito | Tecnología |
|--------|-----------|
| Núcleo | Python 3.12+ (biblioteca estándar: `urllib`, `json`, `zoneinfo`), `pytest`, `ruff` |
| Automatización | GitHub Actions (`schedule`, `workflow_dispatch`, `concurrency`) |
| Acceso a `datos` | Clave de despliegue SSH ed25519 con permiso de escritura + secreto de Actions |
| Fuente de datos | API e·sios de REE, indicador 1001, con secreto `TESTIGO`; `apidatos.ree.es` como respaldo |
| Alojamiento | GitHub Pages (rama principal, carpeta `/docs`) con dominio propio y HTTPS |
| DNS | Registros `CNAME` de `pvcp` y `datos.pvcp` hacia `pvpc-espana.github.io` |
| Frontal | Angular (versión estable vigente), TypeScript, SCSS, Transloco, `Intl` |
| Gráficos | SVG generado por el propio componente (sin librería de gráficos) |
| Pruebas frontal | Vitest (unitarias), Playwright (extremo a extremo, emulación móvil) |
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
