"""historico.json: un registro por día con las medias de España, la más barata,
la provincia rotatoria, el consejo del miércoles y las historias ya publicadas."""
import datetime as dt
import json
from pathlib import Path

from provincias import lista_rotatoria

RUTA = Path(__file__).resolve().parent.parent / "historico.json"
NUM_CONSEJOS = 5  # consejos de «¿Sabías que...?» que se rotan (ver historias.py)


def cargar():
    if RUTA.exists():
        return json.loads(RUTA.read_text(encoding="utf-8"))
    return {"dias": {}}


def guardar(h):
    dias = dict(sorted(h["dias"].items()))
    RUTA.write_text(json.dumps({"dias": dias}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def dia(h, fecha: str):
    return h["dias"].setdefault(fecha, {})


def registrar_medias(h, fecha: str, medias: dict, origen: str):
    d = dia(h, fecha)
    d["media95"] = round(medias["95"], 5) if medias.get("95") else None
    d["mediaDiesel"] = round(medias["diesel"], 5) if medias.get("diesel") else None
    d["media98"] = round(medias["98"], 5) if medias.get("98") else None
    d["origen"] = origen


def _anteriores(h, fecha: str):
    return [f for f in sorted(h["dias"]) if f < fecha]


def provincia_rotatoria(h, fecha: str, fijas):
    """Siguiente provincia de la lista tras la del último día registrado.
    Si hoy ya tiene una asignada, se reutiliza (reintentos el mismo día)."""
    lista = lista_rotatoria(fijas)
    d = dia(h, fecha)
    if d.get("rotatoria") in lista:
        return d["rotatoria"]
    ultima = next((h["dias"][f]["rotatoria"] for f in reversed(_anteriores(h, fecha))
                   if h["dias"][f].get("rotatoria") in lista), None)
    cod = lista[0] if ultima is None else lista[(lista.index(ultima) + 1) % len(lista)]
    d["rotatoria"] = cod
    return cod


def consejo_del_dia(h, fecha: str, disponibles):
    """Consejo de «¿Sabías que...?»: el siguiente al último usado (1→2→…→5→1).
    Si el que toca no tiene datos hoy, se pasa al siguiente que sí los tenga."""
    d = dia(h, fecha)
    if d.get("consejo") in disponibles:
        return d["consejo"]
    usados = [h["dias"][f]["consejo"] for f in _anteriores(h, fecha) if h["dias"][f].get("consejo")]
    ultimo = usados[-1] if usados else 0
    candidatos = sorted(disponibles, key=lambda c: (c - ultimo - 1) % NUM_CONSEJOS)
    return candidatos[0] if candidatos else None


def ultimos_dias(h, fecha: str, n: int, desde_atras=0):
    """Fechas fecha-desde_atras-(n-1) ... fecha-desde_atras, con lo que haya en el histórico."""
    hoy = dt.date.fromisoformat(fecha)
    fechas = [(hoy - dt.timedelta(days=desde_atras + i)).isoformat() for i in range(n - 1, -1, -1)]
    return [(f, h["dias"].get(f)) for f in fechas]
