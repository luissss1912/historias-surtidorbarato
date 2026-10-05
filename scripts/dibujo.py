"""Piezas comunes del diseño (sección 4 del documento): colores, fuentes,
medición de textos, cabecera, banda inferior, píldora de variación y
formato de números. Todo se dibuja en SVG y se convierte a PNG."""
import base64
import datetime as dt
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageFont

ANCHO, ALTO = 1080, 1920
MARGEN = 60
BANDA_Y = 1560

AZUL = "#0a55a6"
AZUL_OSCURO = "#084889"
AMARILLO = "#ffb21a"
CASI_NEGRO = "#121a22"
DISPLAY = "#0b1117"
GRIS = "#9fb0c0"
BLANCO = "#ffffff"
VERDE, VERDE_FONDO = "#14774a", "#e2f3e9"
ROJO, ROJO_FONDO = "#b23a2d", "#f7e2df"
GRIS_PILDORA, GRIS_PILDORA_FONDO = "#4a5866", "#e3e8ee"

RECURSOS = Path(__file__).resolve().parent.parent / "recursos"
FUENTES = RECURSOS / "fuentes"

# family, weight, archivo para medir
F_TITULO = ("Barlow Condensed", 700, "BarlowCondensed-Bold.ttf")
F_SEMI = ("Barlow Condensed", 600, "BarlowCondensed-SemiBold.ttf")
F_TEXTO = ("Barlow", 500, "Barlow-Medium.ttf")
F_PRECIO = ("Share Tech Mono", 400, "ShareTechMono-Regular.ttf")

_cache = {}


def ancho_texto(texto, fuente, tam):
    clave = (fuente[2], tam)
    if clave not in _cache:
        _cache[clave] = ImageFont.truetype(str(FUENTES / fuente[2]), tam)
    return _cache[clave].getlength(texto)


def texto(x, y, contenido, fuente, tam, color, anchor="start", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fuente[0]}" font-weight="{fuente[1]}" '
            f'font-size="{tam}" fill="{color}" text-anchor="{anchor}" {extra}>{escape(contenido)}</text>')


def tam_que_cabe(contenido, fuente, tam_max, ancho_max, tam_min=40):
    tam = tam_max
    while tam > tam_min and ancho_texto(contenido, fuente, tam) > ancho_max:
        tam -= 2
    return tam


def recortar(contenido, fuente, tam, ancho_max):
    if ancho_texto(contenido, fuente, tam) <= ancho_max:
        return contenido
    while contenido and ancho_texto(contenido + "…", fuente, tam) > ancho_max:
        contenido = contenido[:-1]
    return contenido.rstrip() + "…"


def partir_lineas(contenido, fuente, tam, ancho_max):
    lineas, actual = [], ""
    for palabra in contenido.split():
        prueba = (actual + " " + palabra).strip()
        if ancho_texto(prueba, fuente, tam) <= ancho_max:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


# ---------- números ----------

def precio(p):
    """1.80234 -> '1,802' (tres decimales, coma)."""
    return f"{p:.3f}".replace(".", ",")


def euros(v):
    """16.85 -> '16,85 €'. Por encima de 100 sin decimales con punto de miles."""
    if abs(v) >= 100:
        return f"{v:,.0f}".replace(",", ".") + " €"
    return f"{v:.2f}".replace(".", ",") + " €"


def centimos(diferencia_euros):
    """Diferencia en €/l -> céntimos con un decimal ('0,3')."""
    return f"{abs(diferencia_euros) * 100:.1f}".replace(".", ",")


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(f: dt.date):
    return f"{DIAS[f.weekday()].capitalize()}, {f.day} de {MESES[f.month - 1]}"


def fecha_corta(f: dt.date):
    return f.strftime("%d/%m/%Y")


# ---------- piezas ----------

def _icono_data_uri():
    ruta = RECURSOS / "icono.svg"
    if not ruta.exists():
        raise FileNotFoundError("Falta recursos/icono.svg (icono de surtidorbarato.es)")
    return "data:image/svg+xml;base64," + base64.b64encode(ruta.read_bytes()).decode()


def cabecera(color_texto=BLANCO):
    x, y, lado = MARGEN, 160, 96
    return (f'<rect x="{x}" y="{y}" width="{lado}" height="{lado}" rx="20" fill="{AZUL_OSCURO}"/>'
            f'<image x="{x + 4}" y="{y + 4}" width="{lado - 8}" height="{lado - 8}" href="{_icono_data_uri()}"/>'
            + texto(x + lado + 24, y + 66, "SURTIDOR BARATO", F_TITULO, 54, color_texto,
                    extra='letter-spacing="2"'))


def banda_inferior(frase, fondo=CASI_NEGRO, color_frase=BLANCO):
    return (f'<rect x="0" y="{BANDA_Y}" width="{ANCHO}" height="{ALTO - BANDA_Y}" fill="{fondo}"/>'
            + texto(ANCHO / 2, BANDA_Y + 108, frase, F_TEXTO, 46, color_frase, "middle")
            + texto(ANCHO / 2, BANDA_Y + 222, "surtidorbarato.es", F_TITULO, 112, AMARILLO, "middle"))


def pildora(diferencia, x_derecha, y, alto=64, tam=40):
    """Píldora de variación alineada a la derecha. diferencia en €/l (hoy - antes).
    Se compara con precios ya formateados a 3 decimales para que cuadre con lo que se ve."""
    cts = centimos(diferencia)
    if cts == "0,0":
        fondo, color, etiqueta, flecha = GRIS_PILDORA_FONDO, GRIS_PILDORA, "= 0,0 cts", None
    elif diferencia < 0:
        fondo, color, etiqueta, flecha = VERDE_FONDO, VERDE, f"{cts} cts", "abajo"
    else:
        fondo, color, etiqueta, flecha = ROJO_FONDO, ROJO, f"{cts} cts", "arriba"
    tam_flecha = alto * 0.36
    ancho_txt = ancho_texto(etiqueta, F_SEMI, tam)
    ancho = ancho_txt + 48 + (tam_flecha + 14 if flecha else 0)
    x = x_derecha - ancho
    partes = [f'<rect x="{x:.1f}" y="{y}" width="{ancho:.1f}" height="{alto}" rx="{alto / 2}" fill="{fondo}"/>']
    tx = x + 24
    if flecha:
        cx, cy, s = tx + tam_flecha / 2, y + alto / 2, tam_flecha / 2
        if flecha == "abajo":
            pts = f"{cx - s},{cy - s * 0.7} {cx + s},{cy - s * 0.7} {cx},{cy + s * 0.9}"
        else:
            pts = f"{cx - s},{cy + s * 0.7} {cx + s},{cy + s * 0.7} {cx},{cy - s * 0.9}"
        partes.append(f'<polygon points="{pts}" fill="{color}"/>')
        tx += tam_flecha + 14
    partes.append(texto(tx, y + alto / 2 + tam * 0.35, etiqueta, F_SEMI, tam, color))
    return "".join(partes)


def documento(fondo, cuerpo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}">'
            f'<rect width="{ANCHO}" height="{ALTO}" fill="{fondo}"/>{cuerpo}</svg>')


def guardar_png(svg, ruta_png: Path):
    import cairosvg  # necesita la librería de sistema cairo

    ruta_png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(ruta_png),
                     output_width=ANCHO, output_height=ALTO)
    # Instagram solo acepta JPEG: se guarda también una copia .jpg para publicar
    Image.open(ruta_png).convert("RGB").save(ruta_png.with_suffix(".jpg"), "JPEG", quality=95)
