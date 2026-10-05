# Historias diarias de @surtidorbarato

Genera cada día las historias de Instagram de surtidorbarato.es (precio de hoy, top 5 por provincia, «¿Sabías que...?» los miércoles y resumen semanal los domingos) y, cuando se active, las publica solas.

Todo se hace en GitHub Actions, gratis y sin depender de un ordenador encendido.

## Cómo funciona

- Cada media hora se pone en marcha el workflow `Historias diarias`. El script mira la hora de `config.yml` (`hora_publicacion`, ahora las 08:30 de Madrid) y solo trabaja si ya es la hora y ese día no se ha hecho. Así el cambio de hora de verano e invierno no afecta, y la hora se cambia en un solo sitio.
- **Datos:** son los mismos archivos que usa la web (`surtidorbarato.es/datos/…`), así que las cifras coinciden con la web. Si los datos no son de hoy, no se genera nada y se reintenta cada media hora durante `ventana_horas`. Si a esa hora siguen sin actualizarse, el workflow falla y GitHub te avisa por correo.
- **Historial:** `historico.json` guarda las medias de cada día, la más barata, la provincia rotatoria, el consejo del miércoles y las historias publicadas. La primera vez se rellenan las dos semanas anteriores con el histórico del Ministerio, para tener desde el primer día la variación frente a ayer y el resumen del domingo.
- **Imágenes:** se dibujan en SVG y se pasan a PNG de 1080×1920 (`scripts/historias.py`). Se suben a GitHub Pages porque Instagram necesita una dirección pública. Ahí puedes verlas cada día en la página principal de Pages del repositorio.
- **Publicación:** `scripts/publicar.py` las sube en orden (A → B → C → D/E) con la API de Instagram, en JPG porque Instagram no admite PNG. Si una falla, se para y lo reintenta media hora después sin repetir las ya publicadas.

## Puesta en marcha

1. Crea en GitHub un repositorio **público** llamado `historias-surtidorbarato`. Tiene que ser público para que GitHub Pages y las Actions sean gratis.
2. Sube todos los archivos de esta carpeta, incluida la carpeta `.github`. Para ello, entra en **Add file → Upload files** y arrastra el contenido de la carpeta.
3. En **Settings → Pages → Build and deployment → Source**, elige **GitHub Actions**.
4. En **Settings → Actions → General → Workflow permissions**, marca **Read and write permissions** y pulsa Save.
5. En **Actions → Historias diarias → Run workflow**, deja «prueba» y pulsa Run. En unos minutos tendrás las imágenes de hoy en la dirección de Pages, que aparece en el resumen de la ejecución.

A partir de ahí se genera todo solo cada día en **modo prueba**: crea las imágenes, pero no publica nada.

## Activar la publicación en Instagram (más adelante)

1. Comprueba que @surtidorbarato es una cuenta **profesional**.
2. En developers.facebook.com, crea una app con el producto **Instagram → API con inicio de sesión de Instagram**. Pide los permisos `instagram_business_basic` y `instagram_business_content_publish`, y genera un token de larga duración para @surtidorbarato.
3. En el repositorio, entra en **Settings → Secrets and variables → Actions**:
   - En **Secrets**, crea `IG_TOKEN` con el token. Nunca lo pegues en un chat ni en el código.
   - En **Variables**, crea:
     - `IG_USER_ID`: el identificador de la cuenta de Instagram que da la app.
     - `IG_TOKEN_CADUCA`: la fecha en que caduca el token, en formato `AAAA-MM-DD`.
     - `MODO`: `publicar`.
4. Cada mañana se comprueba el token. Si deja de funcionar o le quedan 7 días o menos, el job `token` falla y te llega un correo para renovarlo.

## Probar en local

Las fuentes (Barlow, Barlow Condensed y Share Tech Mono) las descarga el workflow de github.com/google/fonts. Para probar en tu ordenador, ponlas en `recursos/fuentes/`.

```bash
pip install -r requirements.txt
python pruebas/probar.py                                   # pruebas sin red
python scripts/generar.py --dia-json pruebas/dia-2026-10-05.json --consejo 3   # imágenes de ejemplo con datos reales del 05/10
python scripts/generar.py --forzar --modo prueba           # datos de hoy (necesita red)
```

## Criterios (iguales que en la web)

- Las medias de España son de todas las gasolineras con precio. La 95 es la «Gasolina 95 E5».
- «La más barata de España» cuenta solo península y Baleares, porque Canarias, Ceuta y Melilla tienen otros impuestos.
- Los top 5 se ordenan por precio. Si hay empate, se mantiene el orden de la web.
- La provincia rotatoria sigue el orden alfabético de la web sin las cuatro fijas, y empieza por A Coruña.
- El consejo del miércoles se elige entre los cinco con datos reales (del 1 al 5 del documento, rotando). El 6, gasolineras de autovía, no se usa porque la web no tiene ese dato.
