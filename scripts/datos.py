"""Lectura de precios y cálculo de las cifras del día.

Fuente principal: los mismos archivos de datos que usa surtidorbarato.es
(https://surtidorbarato.es/datos/indice.json y /datos/p/{provincia}.json),
que salen de los precios oficiales del Ministerio. Así las cifras de las
historias son exactamente las que se ven en la web.

Fuente secundaria: la API del Ministerio, solo para rellenar días pasados del
histórico (la web no guarda días anteriores).

Regla de oro: nunca se inventa ni se estima un precio. Si falta un dato, la
historia que lo necesita no se genera.
"""
import datetime as dt
import time
from urllib.parse import unquote_plus

import requests

from provincias import PROVINCIAS, NO_PENINSULA

WEB = "https://surtidorbarato.es"
MINISTERIO = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"

# Columnas de /datos/p/{cod}.json (igual que en el JavaScript de la web)
COL = {"id": 0, "marca": 1, "dir": 2, "mun": 3, "prov": 5}
PRECIOS = {"95": 10, "diesel": 11, "98": 12}

# «La más barata de España» en la web: península y Baleares
# (Canarias, Ceuta y Melilla tienen impuestos distintos)
FUERA_DEL_RANKING_ESPANA = {"35", "38", "51", "52"}

CAMPO_MINISTERIO = {"95": "Precio Gasolina 95 E5", "diesel": "Precio Gasoleo A", "98": "Precio Gasolina 98 E5"}


class DatosNoDisponibles(Exception):
    """La fuente no responde o los datos no son del día pedido."""


def _get_json(url, intentos=4, timeout=60):
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "historias-surtidorbarato"})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            ultimo = e
            time.sleep(5 * (i + 1))
    raise DatosNoDisponibles(f"No se pudo descargar {url}: {ultimo}")


def limpiar_nombre(s: str) -> str:
    """Algunos rótulos vienen codificados ('E.s.+Agricola+de+Albal%2c+C.v.')."""
    s = s or ""
    if "%" in s or (" " not in s and "+" in s[1:]):
        s = unquote_plus(s)
    return " ".join(s.split())


# ---------------- web (día de hoy) ----------------

def descargar_web():
    """Devuelve (indice, {cod: [estaciones]})."""
    sello = str(int(time.time()))
    indice = _get_json(f"{WEB}/datos/indice.json?{sello}")
    estaciones = {}
    for fila in indice["provincias"]:
        cod = fila[0]
        estaciones[cod] = _get_json(f"{WEB}/datos/p/{cod}.json?v={indice['version']}")
    return indice, estaciones


def fecha_web(indice) -> dt.date:
    return dt.date.fromisoformat(indice["fecha"]["iso"])


def _media(valores):
    return sum(valores) / len(valores) if valores else None


def _precio(est, tipo):
    v = est[PRECIOS[tipo]] if len(est) > PRECIOS[tipo] else 0
    return v if isinstance(v, (int, float)) and v > 0 else None


def _ficha(est, tipo="95"):
    return {
        "rotulo": limpiar_nombre(est[COL["marca"]]),
        "municipio": limpiar_nombre(est[COL["mun"]]),
        "provincia": PROVINCIAS.get(est[COL["prov"]], ""),
        "precio": _precio(est, tipo),
        "id": est[COL["id"]],
    }


def _ranking(estaciones, tipo="95"):
    """Por precio; en caso de empate se mantiene el orden del archivo, como en la web."""
    con = [e for e in estaciones if _precio(e, tipo) is not None]
    return sorted(con, key=lambda e: _precio(e, tipo))


def resumir(indice, por_provincia):
    todas = [e for lista in por_provincia.values() for e in lista]
    nombres = {fila[0]: fila[1] for fila in indice["provincias"]}

    medias = {t: _media([p for e in todas if (p := _precio(e, t)) is not None]) for t in PRECIOS}
    ranking_es = _ranking([e for e in todas if e[COL["prov"]] not in FUERA_DEL_RANKING_ESPANA])

    provincias = {}
    for cod, lista in por_provincia.items():
        precios95 = [p for e in lista if (p := _precio(e, "95")) is not None]
        provincias[cod] = {
            "nombre": nombres.get(cod) or PROVINCIAS.get(cod, cod),
            "top5": [_ficha(e) for e in _ranking(lista)[:5]],
            "media95": _media(precios95),
            "min95": min(precios95) if precios95 else None,
            "max95": max(precios95) if precios95 else None,
            "num95": len(precios95),
        }

    return {
        "fecha": indice["fecha"]["iso"],
        "actualizado": indice["fecha"].get("isoCompleto"),
        "media95": medias["95"],
        "mediaDiesel": medias["diesel"],
        "media98": medias["98"],
        "barata": _ficha(ranking_es[0]) if ranking_es else None,
        "provincias": provincias,
        "orden_provincias": [fila[0] for fila in indice["provincias"]],
        "no_peninsula": sorted(NO_PENINSULA),
    }


# ---------------- Ministerio (días pasados) ----------------

def medias_ministerio(fecha: dt.date):
    """Medias de España de un día pasado según el histórico del Ministerio."""
    url = f"{MINISTERIO}/EstacionesTerrestresHist/{fecha.strftime('%d-%m-%Y')}"
    crudo = _get_json(url, intentos=2, timeout=90)
    if crudo.get("ResultadoConsulta") != "OK":
        raise DatosNoDisponibles(f"Ministerio: {crudo.get('ResultadoConsulta')}")
    lista = [e for e in crudo["ListaEESSPrecio"] if e.get("Tipo Venta", "P") == "P"]
    out = {}
    for t, campo in CAMPO_MINISTERIO.items():
        valores = []
        for e in lista:
            v = (e.get(campo) or "").strip().replace(",", ".")
            try:
                if v and float(v) > 0:
                    valores.append(float(v))
            except ValueError:
                pass
        out[t] = _media(valores)
    return out
