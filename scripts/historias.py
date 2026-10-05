"""Diseño de cada historia (sección 5 del documento). Cada función devuelve un SVG."""
import datetime as dt

from dibujo import (
    ANCHO, MARGEN, BANDA_Y, AZUL, AZUL_OSCURO, AMARILLO, CASI_NEGRO, DISPLAY, GRIS, BLANCO,
    F_TITULO, F_SEMI, F_TEXTO, F_PRECIO,
    texto, ancho_texto, tam_que_cabe, recortar, partir_lineas,
    precio, euros, fecha_larga, fecha_corta, cabecera, banda_inferior, pildora, documento,
)

ANCHO_UTIL = ANCHO - 2 * MARGEN


def _titulo_con_hoy(y, linea, tam):
    """Línea de título con la palabra final HOY en amarillo."""
    base = linea[: -len("HOY")]
    return (f'<text x="{MARGEN}" y="{y}" font-family="{F_TITULO[0]}" font-weight="{F_TITULO[1]}" '
            f'font-size="{tam}" fill="{BLANCO}">{base}<tspan fill="{AMARILLO}">HOY</tspan></text>')


# ---------------- A. Precio de hoy ----------------

def _tarjeta_precio(y, etiqueta, valor, variacion):
    alto = 340
    partes = [f'<rect x="{MARGEN}" y="{y}" width="{ANCHO_UTIL}" height="{alto}" rx="28" fill="{CASI_NEGRO}"/>',
              texto(MARGEN + 40, y + 78, etiqueta, F_SEMI, 52, GRIS, extra='letter-spacing="3"'),
              pildora(variacion, ANCHO - MARGEN - 40, y + 32)]
    dx, dy, dw, dh = MARGEN + 40, y + 112, ANCHO_UTIL - 80, 196
    partes.append(f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="18" fill="{DISPLAY}"/>')
    num, tam_num, tam_ud = precio(valor), 176, 64
    w = ancho_texto(num, F_PRECIO, tam_num) + 18 + ancho_texto("€/l", F_SEMI, tam_ud)
    x0 = dx + (dw - w) / 2
    base = dy + dh / 2 + tam_num * 0.36
    partes.append(texto(x0, base, num, F_PRECIO, tam_num, AMARILLO))
    partes.append(texto(x0 + w, base, "€/l", F_SEMI, tam_ud, BLANCO, "end"))
    return "".join(partes)


def historia_a(fecha: dt.date, media95, media_diesel, var95, var_diesel, barata_precio):
    c = [cabecera(),
         texto(MARGEN, 410, "PRECIO DE LA", F_TITULO, 132, BLANCO),
         _titulo_con_hoy(536, "GASOLINA HOY", 132),
         texto(MARGEN, 610, f"{fecha_larga(fecha)} · media en España", F_TEXTO, 42, BLANCO),
         _tarjeta_precio(668, "GASOLINA 95", media95, var95),
         _tarjeta_precio(1036, "DIÉSEL", media_diesel, var_diesel)]
    y = 1478
    c.append(texto(MARGEN, y, "La más barata de España:", F_TEXTO, 46, BLANCO))
    c.append(texto(ANCHO - MARGEN, y + 4, "€/l", F_SEMI, 52, BLANCO, "end"))
    c.append(texto(ANCHO - MARGEN - ancho_texto("€/l", F_SEMI, 52) - 14, y + 4,
                   precio(barata_precio), F_PRECIO, 80, AMARILLO, "end"))
    c.append(banda_inferior("Busca la más barata cerca de ti"))
    return documento(AZUL, "".join(c))


# ---------------- B y C. Top 5 ----------------

def historia_top5(fecha: dt.date, nombre_provincia, top5):
    linea2 = f"DE {nombre_provincia.upper()} HOY"
    tam = min(124, tam_que_cabe(linea2, F_TITULO, 124, ANCHO_UTIL, 60))
    c = [cabecera(),
         texto(MARGEN, 340, "TOP 5 · GASOLINA 95", F_SEMI, 52, AMARILLO, extra='letter-spacing="4"'),
         texto(MARGEN, 462, "LAS MÁS BARATAS", F_TITULO, 124, BLANCO),
         _titulo_con_hoy(round(462 + tam * 0.96), linea2, tam)]
    y, alto, hueco = 638, 150, 20
    for i, est in enumerate(top5):
        yy = y + i * (alto + hueco)
        c.append(f'<rect x="{MARGEN}" y="{yy}" width="{ANCHO_UTIL}" height="{alto}" rx="24" fill="{CASI_NEGRO}"/>')
        cx, cy = MARGEN + 66, yy + alto / 2
        c.append(f'<circle cx="{cx}" cy="{cy}" r="40" fill="{AMARILLO}"/>')
        c.append(texto(cx, cy + 19, str(i + 1), F_TITULO, 56, CASI_NEGRO, "middle"))
        # precio en su recuadro de display, a la derecha
        num = precio(est["precio"])
        tam_p = 80
        wp = ancho_texto(num, F_PRECIO, tam_p)
        bx = ANCHO - MARGEN - 24 - wp - 40
        c.append(f'<rect x="{bx:.1f}" y="{yy + 28}" width="{wp + 40:.1f}" height="{alto - 56}" rx="14" fill="{DISPLAY}"/>')
        c.append(texto(ANCHO - MARGEN - 44, cy + tam_p * 0.35, num, F_PRECIO, tam_p, AMARILLO, "end"))
        # nombre y municipio
        x_txt = MARGEN + 136
        ancho_max = bx - 24 - x_txt
        c.append(texto(x_txt, yy + 72, recortar(est["rotulo"], F_SEMI, 58, ancho_max), F_SEMI, 58, BLANCO))
        c.append(texto(x_txt, yy + 120, recortar(est["municipio"], F_TEXTO, 36, ancho_max), F_TEXTO, 36, GRIS))
    c.append(texto(ANCHO / 2, 1515, f"Precios oficiales del Ministerio · €/litro · {fecha_corta(fecha)}",
                   F_TEXTO, 34, BLANCO, "middle", extra='fill-opacity="0.85"'))
    c.append(banda_inferior("¿Y en tu ciudad? Míralo en"))
    return documento(AZUL, "".join(c))


# ---------------- D. ¿Sabías que...? ----------------

def historia_d(frase, cifra, pie):
    c = [cabecera(color_texto=CASI_NEGRO),
         texto(MARGEN, 470, "¿SABÍAS", F_TITULO, 200, CASI_NEGRO),
         texto(MARGEN, 660, "QUE...?", F_TITULO, 200, AZUL)]
    tam = 58
    lineas = partir_lineas(frase, F_TEXTO, tam, ANCHO_UTIL)
    while len(lineas) > 6 and tam > 44:
        tam -= 2
        lineas = partir_lineas(frase, F_TEXTO, tam, ANCHO_UTIL)
    y = 780
    for linea in lineas:
        c.append(texto(MARGEN, y, linea, F_TEXTO, tam, CASI_NEGRO))
        y += tam * 1.3
    caja_y = max(y + 20, 1150)
    caja_h = 1500 - caja_y
    c.append(f'<rect x="{MARGEN}" y="{caja_y:.0f}" width="{ANCHO_UTIL}" height="{caja_h:.0f}" rx="28" fill="{CASI_NEGRO}"/>')
    numero = cifra.removesuffix(" €")
    tam_c = tam_que_cabe(numero + "  ", F_PRECIO, 200, ANCHO_UTIL - 160, 80)
    tam_u = round(tam_c * 0.55)
    w = ancho_texto(numero, F_PRECIO, tam_c) + 16 + ancho_texto("€", F_SEMI, tam_u)
    x0, base = (ANCHO - w) / 2, caja_y + caja_h / 2 + tam_c * 0.22
    c.append(texto(x0, base, numero, F_PRECIO, tam_c, AMARILLO))
    c.append(texto(x0 + w, base, "€", F_SEMI, tam_u, BLANCO, "end"))
    c.append(texto(ANCHO / 2, caja_y + caja_h - 40, pie, F_TEXTO, 40, GRIS, "middle"))
    c.append(banda_inferior("Compara antes de repostar en", fondo=AZUL))
    return documento(AMARILLO, "".join(c))


# ---------------- E. Resumen semanal ----------------

def _tarjeta_semana(y, alto, etiqueta, media, anterior):
    partes = [f'<rect x="{MARGEN}" y="{y}" width="{ANCHO_UTIL}" height="{alto}" rx="28" fill="{CASI_NEGRO}"/>',
              texto(MARGEN + 40, y + 70, etiqueta, F_SEMI, 48, GRIS, extra='letter-spacing="3"'),
              pildora(round(media, 3) - round(anterior, 3), ANCHO - MARGEN - 40, y + 26)]
    tam = 120 if alto < 300 else 150
    base = y + 70 + tam * 0.95
    partes.append(texto(MARGEN + 40, base, precio(media), F_PRECIO, tam, AMARILLO))
    partes.append(texto(MARGEN + 40 + ancho_texto(precio(media), F_PRECIO, tam) + 14, base,
                        "€/l", F_SEMI, 56, BLANCO))
    partes.append(texto(ANCHO - MARGEN - 40, base, f"Semana anterior: {precio(anterior)}",
                        F_TEXTO, 36, GRIS, "end"))
    return "".join(partes)


def _grafica(y, alto, serie95, serie_diesel, etiquetas):
    """Dos líneas apiladas (95 arriba, diésel abajo), cada una con su escala para que
    se vea la tendencia de la semana. Se rotulan el primer y el último valor."""
    x0, x1 = MARGEN + 70, ANCHO - MARGEN - 190
    p = [f'<rect x="{MARGEN}" y="{y}" width="{ANCHO_UTIL}" height="{alto}" rx="28" fill="{CASI_NEGRO}"/>',
         texto(MARGEN + 40, y + 60, "ÚLTIMOS 7 DÍAS", F_SEMI, 40, GRIS, extra='letter-spacing="3"')]

    def px(i):
        return x0 + i * (x1 - x0) / (len(etiquetas) - 1)

    franja = (alto - 150) / 2
    for k, (serie, color, nombre) in enumerate(((serie95, AMARILLO, "Gasolina 95"), (serie_diesel, BLANCO, "Diésel"))):
        top = y + 90 + k * franja
        gy0, gy1 = top + 16, top + franja - 16
        vmin, vmax = min(serie), max(serie)
        if vmax - vmin < 0.01:  # escala mínima de 1 céntimo para no exagerar cambios pequeños
            centro = (vmax + vmin) / 2
            vmin, vmax = centro - 0.005, centro + 0.005

        def py(v, gy0=gy0, gy1=gy1, vmin=vmin, vmax=vmax):
            return gy1 - (v - vmin) / (vmax - vmin) * (gy1 - gy0)

        puntos = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(serie))
        p.append(f'<polyline points="{puntos}" fill="none" stroke="{color}" stroke-width="7" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(serie):
            p.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="{12 if i == len(serie) - 1 else 8}" fill="{color}"/>')
        ultimo = serie[-1]
        p.append(texto(x1 + 30, py(ultimo) + 4, precio(ultimo), F_PRECIO, 44, color))
        p.append(texto(x1 + 30, py(ultimo) + 40, nombre, F_TEXTO, 28, GRIS))
    for i, e in enumerate(etiquetas):
        p.append(texto(px(i), y + alto - 30, e, F_SEMI, 36, GRIS, "middle"))
    return "".join(p)


def historia_e(semana95, anterior95, semana_d, anterior_d, grafica=None):
    """grafica = (serie95, serie_diesel, etiquetas) o None si no hay 7 días."""
    c = [cabecera(),
         texto(MARGEN, 410, "LA SEMANA EN", F_TITULO, 132, BLANCO),
         texto(MARGEN, 536, "LA GASOLINERA", F_TITULO, 132, AMARILLO),
         texto(MARGEN, 606, "Media de los últimos 7 días en España", F_TEXTO, 42, BLANCO)]
    if grafica:
        c.append(_tarjeta_semana(650, 250, "GASOLINA 95", semana95, anterior95))
        c.append(_tarjeta_semana(920, 250, "DIÉSEL", semana_d, anterior_d))
        c.append(_grafica(1190, 340, *grafica))
    else:
        c.append(_tarjeta_semana(680, 360, "GASOLINA 95", semana95, anterior95))
        c.append(_tarjeta_semana(1080, 360, "DIÉSEL", semana_d, anterior_d))
    c.append(banda_inferior("Precios de hoy en"))
    return documento(AZUL, "".join(c))
