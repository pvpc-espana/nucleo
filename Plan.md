# Plan de implementación por fases

Cada fase termina con un entregable verificable. Las fases 1–3 (datos) y 4 (frontal
base) pueden avanzar en paralelo una vez cerrado el formato de datos de la fase 1.

Arquitectura, formato de datos y tecnologías: ver [`README.md`](README.md).

---

## Fase 0 · Preparación de la infraestructura

**Objetivo:** que los tres repositorios y los dominios estén listos para publicar.

- [ ] Confirmar el dominio definitivo (`pvcp.linaresdigital.com` frente a
      `pvpc.linaresdigital.com`) y usarlo de forma coherente en todo el proyecto.
- [ ] DNS: crear `CNAME pvcp → pvpc-espana.github.io` y
      `CNAME datos.pvcp → pvpc-espana.github.io`.
- [ ] Verificar el dominio `linaresdigital.com` en la organización de GitHub
      (*Settings → Pages → Verified domains*) para evitar apropiaciones de subdominios.
- [ ] Generar la clave de despliegue ed25519 (README §3.3):
  - pública en `datos` → *Deploy keys* con escritura;
  - privada en `nucleo` → secreto `DATOS_DEPLOY_KEY`.
- [ ] Proteger la rama principal de `datos` permitiendo el push de la clave de
      despliegue (o dejarla sin protección si sólo escribe el núcleo).
- [ ] Guardar el *token* de e·sios en `nucleo` como secreto de Actions `TESTIGO`.

**Hecho cuando:** los registros DNS resuelven y el secreto está creado.

## Fase 1 · Núcleo: obtención y normalización de datos

**Objetivo:** un comando Python que, dada una fecha, genera el JSON v1 del día.

- [ ] Estructura del paquete `pvpc/`, `pyproject.toml`, configuración de `ruff` y `pytest`.
- [ ] Explorar la respuesta real de e·sios (indicador 1001) y de `apidatos.ree.es`
      y documentarlas con ejemplos
      guardados en `tests/fixtures/` (día normal, día de 23 h, día de 25 h, día no
      publicado aún, error del servidor).
- [ ] Validar la granularidad del PVPC (horaria o cuartohoraria) y fijar `resolucion`.
- [ ] Cliente `fuente_esios.py` que lee el *token* de la variable de entorno
      `TESTIGO`, con tiempo de espera, reintentos con espera exponencial y cabecera
      `User-Agent` identificativa; sin exponer el *token* en registros.
- [ ] Cliente de respaldo `fuente_ree.py` (`apidatos.ree.es`) usado sólo si e·sios falla.
- [ ] `normalizar.py`: selección de la serie PVPC, conversión €/MWh → €/kWh,
      redondeo a 5 decimales, `inicio` con desfase horario `Europe/Madrid`, cálculo
      de `resumen` (mín., máx., media).
- [ ] Validaciones: número de periodos coherente con el día (23/24/25 h o
      92/96/100 cuartos), precios numéricos y dentro de un rango razonable; un día
      incompleto **no se publica**.
- [ ] Tests unitarios con las *fixtures* (sin red).

**Hecho cuando:** `python -m pvpc --fecha 2026-10-25 --salida /tmp/x` genera un JSON
válido y los tests pasan.

## Fase 2 · Núcleo: workflow y publicación en `datos`

**Objetivo:** ejecución automática 4 veces al día que publica sólo si hay cambios.

- [ ] `publicar.py`: escribe `v1/AAAA/MM/AAAA-MM-DD.json` con serialización
      determinista (claves ordenadas, sangría fija, salto de línea final) y
      actualiza `indice.json` **sólo** si algún fichero diario cambió.
- [ ] Lógica de fechas: siempre hoy y mañana en `Europe/Madrid`; mañana sin publicar
      no es error. Parámetro opcional para fechas concretas o rangos.
- [ ] `.github/workflows/actualizar.yml`:
  - `schedule` con los 4 cron de README §3.2 y `workflow_dispatch` (fecha opcional);
  - `concurrency: actualizar-datos` para evitar ejecuciones solapadas;
  - checkout de `nucleo` y de `datos` (ruta `datos/`, `ssh-key: DATOS_DEPLOY_KEY`);
  - `env: TESTIGO: ${{ secrets.TESTIGO }}` sólo en el paso que consulta la API;
  - ejecución del comando, `git status --porcelain` y commit/push sólo si hay
    cambios, con mensaje tipo `PVPC 2026-10-25` y autor bot identificable;
  - permisos mínimos (`contents: read` en `nucleo`).
- [ ] `.github/workflows/pruebas.yml`: `ruff` + `pytest` en cada push y PR.
- [ ] Mantenimiento del cron: evitar la desactivación por 60 días de inactividad
      (p. ej. workflow mensual que reactiva el workflow vía API o commit de
      mantenimiento en `nucleo`).
- [ ] Alertas: el fallo del workflow notifica por correo a los responsables;
      opcionalmente abrir una *issue* automática si mañana no se ha publicado a las
      23:37.

**Hecho cuando:** dos ejecuciones manuales seguidas producen un único commit en
`datos` (la segunda no cambia nada).

## Fase 3 · Repositorio `datos`

**Objetivo:** datos accesibles en `https://datos.pvcp.linaresdigital.com/v1/...`.

- [ ] Estructura inicial `docs/` con `CNAME`, `.nojekyll`, `index.html` informativo y
      `v1/indice.json`.
- [ ] Activar GitHub Pages (rama principal, carpeta `/docs`), dominio propio y
      «Enforce HTTPS».
- [ ] README de `datos` con el formato v1, política de versiones y licencia/origen.
- [ ] Carga histórica (*backfill*) desde la fecha de inicio elegida mediante
      `workflow_dispatch` por rangos, para que el frontal tenga días anteriores.
- [ ] Comprobar desde un navegador que `fetch` desde otro origen funciona (CORS).

**Hecho cuando:** `curl https://datos.pvcp.linaresdigital.com/v1/indice.json`
devuelve el índice con HTTPS válido.

## Fase 4 · Frontal: base de la aplicación

**Objetivo:** SPA publicada que muestra los precios de un día.

- [ ] Crear proyecto Angular (standalone, SCSS, *signals*, sin SSR) en `frontal`.
- [ ] Configurar compilación en `/docs` (`outputPath: { base: "docs", browser: "" }`),
      `CNAME`, `.nojekyll` y copia de `index.html` como `404.html` tras el build.
- [ ] Rutas: `/:idioma/:fecha` (por defecto hoy en `Europe/Madrid`), con validación
      de fecha y redirección de rutas desconocidas.
- [ ] `PreciosService`: URL base configurable por entorno, caché en memoria,
      404 → día sin datos, errores de red con mensaje y reintento.
- [ ] Componente de día *mobile-first*:
  - cabecera con fecha y resumen (mín., máx., media, precio actual);
  - gráfico de barras SVG + lista de horas con color por tramo (barato/medio/caro);
  - hora actual resaltada y desplazada a la vista;
  - **rejilla fija de horas** (23/24/25 según el día) también cuando no hay datos,
    con un aviso «Precios aún no publicados» sin alterar el diseño.
- [ ] Workflow de `frontal`: en cada push a la rama principal, lint + tests + build y
      commit de `/docs` si cambia (ignorando cambios en `docs/**` para no entrar en
      bucle), o build local documentado si se prefiere.
- [ ] Activar GitHub Pages con dominio `pvcp.linaresdigital.com` y HTTPS.

**Hecho cuando:** `https://pvcp.linaresdigital.com/es/<hoy>` muestra los precios reales.

## Fase 5 · Frontal: navegación entre días

**Objetivo:** pasar de día sin recargar, con dedo, botones o teclado.

- [ ] Botones «anterior/siguiente» en la parte **superior e inferior**, con etiquetas
      accesibles; el siguiente se deshabilita más allá del último día disponible
      según `indice.json` (permitiendo «mañana» aunque esté pendiente).
- [ ] Directiva de deslizamiento con *Pointer Events*: umbral de distancia/velocidad,
      sin interferir con el *scroll* vertical (`touch-action: pan-y`).
      Deslizar a la izquierda → día siguiente; a la derecha → día anterior.
- [ ] Animación de transición entre días respetando `prefers-reduced-motion`.
- [ ] Flechas ← → del teclado y botón «Hoy».
- [ ] Precarga del día anterior y siguiente; actualización de la URL con
      `Router.navigate` (historial del navegador coherente).
- [ ] Refresco automático del día en curso/siguiente al volver a la pestaña tras
      las ~20:30 si aún no había datos.

**Hecho cuando:** en un móvil real se recorren varios días deslizando sin recargas ni
saltos de diseño.

## Fase 6 · Internacionalización

**Objetivo:** interfaz completa en es, en, fr, de, it y pt.

- [ ] Integrar Transloco con carga perezosa de `assets/i18n/{es,en,fr,de,it,pt}.json`.
- [ ] Idioma en la URL (`/en/2026-10-24`), detección inicial por
      `navigator.language`, selector visible y preferencia guardada en `localStorage`.
- [ ] Formato de fechas, números y moneda con `Intl` según el idioma
      (p. ej. `0,12345 €/kWh` frente a `€0.12345/kWh`).
- [ ] Actualizar `<html lang>`, `<title>` y meta descripción al cambiar de idioma;
      etiquetas `hreflang` en `index.html`.
- [ ] Revisión de traducciones por hablantes nativos o fuente fiable; test que
      verifica que todos los ficheros tienen las mismas claves.

**Hecho cuando:** cambiar de idioma traduce toda la interfaz sin recargar y todos los
ficheros de idioma están completos.

## Fase 7 · Calidad, accesibilidad y rendimiento

- [ ] Tests unitarios (Vitest) de servicio, utilidades de fecha y tramos de precio.
- [ ] Tests E2E (Playwright) con emulación móvil: carga, deslizamiento, botones,
      día sin datos, día de 23/25 horas, cambio de idioma.
- [ ] Accesibilidad WCAG 2.1 AA: contraste de los colores de tramo, información no
      transmitida sólo por color, foco visible, lectores de pantalla.
- [ ] Lighthouse móvil ≥ 90 en rendimiento, accesibilidad y buenas prácticas.
- [ ] Modo oscuro según `prefers-color-scheme`.
- [ ] Metadatos para compartir (Open Graph) e icono/manifest básico.

## Fase 8 · Puesta en producción y operación

- [ ] Revisión final de secretos y permisos (clave de despliegue sólo en `datos`,
      permisos mínimos en workflows).
- [ ] Vigilar una semana completa de ejecuciones, incluido un cambio de hora si cae
      en el periodo.
- [ ] Documentar el procedimiento de rotación de la clave de despliegue y de
      recarga manual de datos.
- [ ] Publicar la v1.0 (etiquetas en los tres repositorios).

## Ampliaciones futuras

- PVPC de Ceuta y Melilla y opción de hora canaria.
- PWA instalable con caché sin conexión y notificaciones de horas baratas.
- Vistas semanal/mensual e histórico comparativo.
- Exportación CSV y widget embebible.
