"""Reel diario: «La gasolinera más barata de España hoy» (vídeo 1080×1920, ~12 s, sin música).

Se dibuja fotograma a fotograma en SVG (mismo estilo que las historias) y se une con ffmpeg.
Las cifras solo aparecen con su valor real: el efecto de «display» va escribiendo los dígitos
del precio verdadero (1 → 1, → 1,4 → 1,46 → 1,465), nunca muestra precios intermedios.

Zonas seguras de Reels: arriba ~220 px (cabecera de la app) y abajo ~420 px (texto del post y
botones), y a la derecha ~140 px (botones de me gusta, comentar…). El contenido va dentro.
"""
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from dibujo import (
    ANCHO, ALTO, MARGEN, AZUL, AMARILLO, CASI_NEGRO, DISPLAY, GRIS, BLANCO, VERDE, VERDE_FONDO,
    F_TITULO, F_SEMI, F_TEXTO, F_PRECIO,
    texto, ancho_texto, tam_que_cabe, recortar, precio, euros, documento, guardar_png, cabecera,
)

FPS = 30
DURACION = 12.0
X0, X1 = MARGEN, ANCHO - 150          # deja libre la columna de botones de la derecha
UTIL = X1 - X0


def suave(t):
    """0→1 con aceleración y frenada."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def aparece(t, inicio, dur=0.45):
    return suave((t - inicio) / dur)


def grupo(contenido, opacidad, dy=0.0):
    if opacidad <= 0:
        return ""
    return f'<g opacity="{opacidad:.3f}" transform="translate(0 {dy:.1f})">{contenido}</g>'


def escribir(valor_txt, t, inicio, por_caracter=0.12):
    """Muestra el precio real carácter a carácter, como un display que se enciende."""
    n = int(max(0.0, t - inicio) / por_caracter) + 1 if t >= inicio else 0
    return valor_txt[:min(n, len(valor_txt))]


def fotograma(t, d):
    c = []
    # Cabecera de la marca (siempre)
    c.append(grupo(cabecera(y=250), aparece(t, 0.0, 0.3)))

    # 1) Gancho
    a = aparece(t, 0.15)
    c.append(grupo(texto(X0, 500, "¿DÓNDE ESTÁ LA", F_TITULO, 104, BLANCO)
                   + texto(X0, 610, "GASOLINA MÁS", F_TITULO, 104, BLANCO)
                   + f'<text x="{X0}" y="720" font-family="{F_TITULO[0]}" font-weight="{F_TITULO[1]}" '
                     f'font-size="104" fill="{BLANCO}">BARATA <tspan fill="{AMARILLO}">HOY</tspan>?</text>',
                   a, (1 - a) * 40))

    # 2) Tarjeta tipo surtidor con la más barata de España
    a = aparece(t, 2.2)
    y = 790
    tarjeta = [f'<rect x="{X0}" y="{y}" width="{UTIL}" height="470" rx="30" fill="{CASI_NEGRO}"/>',
               texto(X0 + 40, y + 76, "LA MÁS BARATA DE ESPAÑA · GASOLINA 95", F_SEMI, 40, GRIS,
                     extra='letter-spacing="2"'),
               f'<rect x="{X0 + 40}" y="{y + 110}" width="{UTIL - 80}" height="210" rx="20" fill="{DISPLAY}"/>']
    num = escribir(precio(d["barata"]["precio"]), t, 2.7)
    tam = 190
    w_total = ancho_texto(precio(d["barata"]["precio"]), F_PRECIO, tam) + 18 + ancho_texto("€/l", F_SEMI, 66)
    xn = X0 + (UTIL - w_total) / 2
    tarjeta.append(texto(xn, y + 285, num, F_PRECIO, tam, AMARILLO))
    if num == precio(d["barata"]["precio"]):
        tarjeta.append(texto(xn + w_total, y + 285, "€/l", F_SEMI, 66, BLANCO, "end"))
    a2 = aparece(t, 3.6)
    nombre = recortar(d["barata"]["rotulo"], F_SEMI, 62, UTIL - 80)
    mun, prov = d["barata"]["municipio"], d["barata"]["provincia"]
    lugar = recortar(mun if mun.lower() == prov.lower() else f"{mun} ({prov})", F_TEXTO, 40, UTIL - 80)
    tarjeta.append(grupo(texto(X0 + 40, y + 392, nombre, F_SEMI, 62, BLANCO)
                         + texto(X0 + 40, y + 442, lugar, F_TEXTO, 40, GRIS), a2, (1 - a2) * 20))
    c.append(grupo("".join(tarjeta), a, (1 - a) * 60))

    # 3) Comparación con la media y ahorro por depósito
    a = aparece(t, 5.6)
    linea = (texto(X0, 1345, "Media en España:", F_TEXTO, 46, BLANCO)
             + texto(X1, 1345, "€/l", F_SEMI, 44, BLANCO, "end")
             + texto(X1 - ancho_texto("€/l", F_SEMI, 44) - 12, 1345, precio(d["media95"]), F_PRECIO, 56, BLANCO, "end"))
    c.append(grupo(linea, a, (1 - a) * 30))
    a = aparece(t, 7.0)
    pill_txt = f'Ahorras {d["ahorro"]} en un depósito de {d["litros"]} l'
    tam_p = tam_que_cabe(pill_txt, F_SEMI, 52, UTIL - 60, 36)
    wp = ancho_texto(pill_txt, F_SEMI, tam_p) + 60
    escala = 0.85 + 0.15 * a
    cx = X0 + wp / 2
    pill = (f'<g transform="translate({cx:.1f} 1440) scale({escala:.3f}) translate({-cx:.1f} -1440)">'
            f'<rect x="{X0}" y="1395" width="{wp:.1f}" height="90" rx="45" fill="{VERDE_FONDO}"/>'
            + texto(X0 + 30, 1457, pill_txt, F_SEMI, tam_p, VERDE) + '</g>')
    c.append(grupo(pill, a))

    # 4) Llamada a la acción (ocupa la pantalla al final)
    a = aparece(t, 9.3, 0.5)
    if a > 0:
        cta = (f'<rect x="0" y="0" width="{ANCHO}" height="{ALTO}" fill="{CASI_NEGRO}"/>'
               + texto(ANCHO / 2, 700, "¿Y la más barata", F_TITULO, 110, BLANCO, "middle")
               + texto(ANCHO / 2, 820, "cerca de ti?", F_TITULO, 110, BLANCO, "middle")
               + texto(ANCHO / 2, 1010, "surtidorbarato.es", F_TITULO, 120, AMARILLO, "middle")
               + texto(ANCHO / 2, 1120, "Síguenos para verla cada mañana", F_TEXTO, 48, GRIS, "middle"))
        c.append(grupo(cta, a))
    return documento(AZUL, "".join(c))


def generar_reel(d, ruta_mp4: Path):
    """d: {barata:{rotulo,municipio,provincia,precio}, media95, ahorro (texto), litros}"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Falta ffmpeg para hacer el Reel")
    tmp = Path(tempfile.mkdtemp())
    try:
        n = int(DURACION * FPS)
        anterior = None
        for i in range(n):
            svg = fotograma(i / FPS, d)
            png = tmp / f"f{i:04d}.png"
            if svg == anterior:  # fotograma igual al anterior: se copia
                shutil.copyfile(tmp / f"f{i - 1:04d}.png", png)
            else:
                guardar_png(svg, png, jpg=False)
            anterior = svg
        ruta_mp4.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(ruta_mp4)], check=True)
        # Portada (fotograma con la tarjeta completa) para la vista previa
        shutil.copyfile(tmp / f"f{int(8.5 * FPS):04d}.png", ruta_mp4.with_suffix(".png"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import sys
    datos = {"barata": {"rotulo": "Oil Prix", "municipio": "Tarragona", "provincia": "Tarragona", "precio": 1.465},
             "media95": 1.802457, "ahorro": euros((round(1.802457, 3) - 1.465) * 50), "litros": 50}
    generar_reel(datos, Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/reel.mp4"))
