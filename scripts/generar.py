"""Genera las historias del día.

Uso normal (lo lanza GitHub Actions cada media hora):
    python scripts/generar.py
Decide solo si toca: a partir de la hora de config.yml, con datos de hoy y si
no se ha hecho ya. Con --forzar se salta la comprobación de la hora.

Deja en publico/AAAA-MM-DD/ los PNG (para revisar), los JPG (para Instagram),
manifest.json (orden de publicación) y un index.html para verlos.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datos  # noqa: E402
import historico as hist  # noqa: E402
from dibujo import guardar_png, precio, euros, centimos  # noqa: E402
from historias import historia_a, historia_top5, historia_d, historia_e  # noqa: E402
from provincias import PROVINCIAS, NO_PENINSULA  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
LETRAS_DIA = ["L", "M", "X", "J", "V", "S", "D"]


def cfg():
    return yaml.safe_load((RAIZ / "config.yml").read_text(encoding="utf-8"))


def salida_github(**kv):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def slug(nombre):
    import unicodedata
    s = unicodedata.normalize("NFD", nombre.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() else "-" for c in s).strip("-").replace("--", "-")


def r3(x):
    return round(x, 3)


# ---------------- ¿Sabías que...? ----------------

def consejos_posibles(dia, cod_rot, litros):
    """Devuelve {número: (frase, cifra, pie)} solo con los consejos que tienen datos reales hoy."""
    out = {}
    prov = dia["provincias"].get(cod_rot) or {}
    nombre = PROVINCIAS[cod_rot]
    if prov.get("max95") and prov.get("min95") and prov["max95"] > prov["min95"]:
        dif = r3(prov["max95"]) - r3(prov["min95"])
        out[1] = (f"En {nombre}, entre la gasolinera más cara y la más barata hay hoy "
                  f"{centimos(dif)} céntimos por litro de gasolina 95. En un depósito de {litros} litros:",
                  euros(dif * litros), "de diferencia por depósito")
    pen = {c: p["media95"] for c, p in dia["provincias"].items() if c not in NO_PENINSULA and p.get("media95")}
    if len(pen) >= 2:
        cara = max(pen, key=pen.get)
        barata = min(pen, key=pen.get)
        dif = r3(pen[cara]) - r3(pen[barata])
        out[2] = (f"La gasolina 95 más cara de la península está hoy en {PROVINCIAS[cara]} "
                  f"({precio(pen[cara])} €/l de media) y la más barata en {PROVINCIAS[barata]} "
                  f"({precio(pen[barata])} €/l). Por cada depósito de {litros} litros:",
                  euros(dif * litros), "de diferencia entre una y otra")
    if dia.get("media95") and dia.get("barata"):
        dif = r3(dia["media95"]) - r3(dia["barata"]["precio"])
        out[3] = (f"La gasolinera más barata de España vende hoy la gasolina 95 a "
                  f"{precio(dia['barata']['precio'])} €/l, frente a una media de "
                  f"{precio(dia['media95'])} €/l. En un depósito de {litros} litros:",
                  euros(dif * litros), "de ahorro por depósito")
    if dia.get("media98") and dia.get("media95"):
        dif = r3(dia["media98"]) - r3(dia["media95"])
        out[4] = (f"La gasolina 98 cuesta hoy de media {centimos(dif)} céntimos más por litro "
                  f"que la 95. Llenar un depósito de {litros} litros con 98 te cuesta:",
                  "+" + euros(dif * litros), "más que con gasolina 95")
    if prov.get("media95") and prov.get("min95") and prov["media95"] > prov["min95"]:
        dif = r3(prov["media95"]) - r3(prov["min95"])
        out[5] = (f"Si llenas un depósito de {litros} litros a la semana en la gasolinera más "
                  f"barata de {nombre} en vez de pagar la media de la provincia, con los precios "
                  f"de hoy ahorras:", euros(dif * litros * 52), "al año (52 depósitos)")
    return out


# ---------------- programa ----------------

def toca_hoy(c, ahora, h, modo):
    hh, mm = map(int, c["hora_publicacion"].split(":"))
    inicio = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    fin = inicio + dt.timedelta(hours=c["ventana_horas"])
    if not (inicio <= ahora < fin):
        return False, f"Fuera de horario (publicación a las {c['hora_publicacion']}, ahora {ahora:%H:%M})", fin
    estado = h["dias"].get(ahora.date().isoformat(), {}).get("estado")
    if estado == "publicado" or (modo == "prueba" and estado in ("generado", "publicado")):
        return False, "Las historias de hoy ya están hechas", fin
    return True, "", fin


def completar_historico(h, hoy: dt.date):
    """Rellena con el histórico del Ministerio los días que falten: siempre ayer (para la
    variación) y, los domingos, las dos últimas semanas (para el resumen). Si el Ministerio
    no responde dos veces seguidas, se deja para otro día."""
    dias = 13 if hoy.weekday() == 6 else 1
    fallos = 0
    for i in range(1, dias + 1):
        f = hoy - dt.timedelta(days=i)
        if h["dias"].get(f.isoformat(), {}).get("media95"):
            continue
        try:
            hist.registrar_medias(h, f.isoformat(), datos.medias_ministerio(f), "ministerio-historico")
            print(f"  Histórico completado: {f}")
            fallos = 0
        except datos.DatosNoDisponibles as e:
            print(f"  Sin histórico para {f}: {e}")
            fallos += 1
            if fallos >= 2:
                print("  El Ministerio no responde; el histórico se completará otro día.")
                return


def generar(dia, h, c, salida: Path, consejo_forzado=None, solo_estas=None):
    fecha = dt.date.fromisoformat(dia["fecha"])
    f = fecha.isoformat()
    carpeta = salida / f
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    historias, omitidas = [], []

    def añadir(clave, nombre, svg_fn):
        if solo_estas and clave.split("-")[0] not in solo_estas:
            return
        archivo = f"{f}_{nombre}.png"
        guardar_png(svg_fn(), carpeta / archivo)
        historias.append({"clave": clave, "png": archivo, "jpg": archivo.replace(".png", ".jpg")})
        print(f"  ✓ {archivo}")

    # A. Precio de hoy
    ayer = h["dias"].get((fecha - dt.timedelta(days=1)).isoformat(), {})
    if all([dia.get("media95"), dia.get("mediaDiesel"), dia.get("barata"), ayer.get("media95"), ayer.get("mediaDiesel")]):
        añadir("A", "A_precio-hoy", lambda: historia_a(
            fecha, dia["media95"], dia["mediaDiesel"],
            r3(dia["media95"]) - r3(ayer["media95"]), r3(dia["mediaDiesel"]) - r3(ayer["mediaDiesel"]),
            dia["barata"]["precio"]))
    else:
        omitidas.append("A: faltan las medias de hoy o de ayer, o la más barata de España")

    # B. Provincias fijas y C. rotatoria
    cod_rot = hist.provincia_rotatoria(h, f, c["provincias_fijas"])
    for clave, cod in [("B", x) for x in c["provincias_fijas"]] + [("C", cod_rot)]:
        p = dia["provincias"].get(cod)
        nombre = (p or {}).get("nombre") or PROVINCIAS[cod]
        if p and len(p.get("top5", [])) == 5:
            añadir(f"{clave}-{cod}", f"{clave}_top5-{slug(nombre)}",
                   lambda p=p, nombre=nombre: historia_top5(fecha, nombre, p["top5"]))
        else:
            omitidas.append(f"{clave} {nombre}: no hay 5 gasolineras con precio de gasolina 95")

    # D. ¿Sabías que...? (miércoles)
    if fecha.weekday() == 2 or consejo_forzado:
        posibles = consejos_posibles(dia, cod_rot, c["litros_deposito"])
        n = consejo_forzado if consejo_forzado in posibles else hist.consejo_del_dia(h, f, list(posibles))
        if n:
            hist.dia(h, f)["consejo"] = n
            añadir("D", "D_sabias-que", lambda: historia_d(*posibles[n]))
        else:
            omitidas.append("D: ningún consejo tiene datos hoy")

    # E. Resumen semanal (domingos)
    if fecha.weekday() == 6:
        esta = hist.ultimos_dias(h, f, 7)
        anterior = hist.ultimos_dias(h, f, 7, desde_atras=7)
        completos = all(d and d.get("media95") and d.get("mediaDiesel") for _, d in esta + anterior)
        if completos:
            s95 = [d["media95"] for _, d in esta]
            sd = [d["mediaDiesel"] for _, d in esta]
            a95 = [d["media95"] for _, d in anterior]
            ad = [d["mediaDiesel"] for _, d in anterior]
            etiquetas = [LETRAS_DIA[dt.date.fromisoformat(x).weekday()] for x, _ in esta]
            añadir("E", "E_resumen-semanal", lambda: historia_e(
                sum(s95) / 7, sum(a95) / 7, sum(sd) / 7, sum(ad) / 7, (s95, sd, etiquetas)))
        else:
            omitidas.append("E: faltan días en el histórico de las dos últimas semanas")

    (carpeta / "manifest.json").write_text(json.dumps(
        {"fecha": f, "historias": historias, "omitidas": omitidas}, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_indice(salida, f, historias, omitidas)
    return historias, omitidas


def escribir_indice(salida, f, historias, omitidas):
    tarjetas = "".join(f'<figure><img src="{f}/{x["png"]}" alt="{x["clave"]}"><figcaption>{x["png"]}</figcaption></figure>'
                       for x in historias)
    avisos = "".join(f"<li>{o}</li>" for o in omitidas) or "<li>Ninguna</li>"
    (salida / "index.html").write_text(f"""<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Historias {f}</title>
<style>body{{font-family:system-ui;background:#0a55a6;color:#fff;margin:0;padding:16px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}
img{{width:100%;border-radius:12px;display:block}}figcaption{{font-size:13px;opacity:.8;margin-top:4px}}
figure{{margin:0}}</style><h1>Historias del {f}</h1><div class="g">{tarjetas}</div>
<h2>No generadas</h2><ul>{avisos}</ul></html>""", encoding="utf-8")


def asegurar_icono():
    ruta = RAIZ / "recursos" / "icono.svg"
    if ruta.exists():
        return
    import requests
    r = requests.get("https://surtidorbarato.es/icono.svg", timeout=30)
    r.raise_for_status()
    ruta.write_bytes(r.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["prueba", "publicar"])
    ap.add_argument("--forzar", action="store_true", help="no comprobar la hora")
    ap.add_argument("--comprobar", action="store_true", help="solo decir si toca generar ahora")
    ap.add_argument("--salida", default=str(RAIZ / "publico"))
    ap.add_argument("--dia-json", help="(pruebas) usar este resumen del día en vez de descargarlo")
    ap.add_argument("--consejo", type=int, help="(pruebas) forzar un consejo de «¿Sabías que...?»")
    ap.add_argument("--solo", help="(pruebas) solo estas historias, p. ej. A,B")
    args = ap.parse_args()

    c = cfg()
    modo = args.modo or os.environ.get("MODO") or c["modo"]
    tz = ZoneInfo(c["zona_horaria"])
    ahora = dt.datetime.now(tz)
    h = hist.cargar()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    asegurar_icono()

    if args.dia_json:  # modo de pruebas con datos ya preparados: no toca el histórico real
        dia = json.loads(Path(args.dia_json).read_text(encoding="utf-8"))
        h = {"dias": dia.pop("historico", {})}
        solo = set(args.solo.split(",")) if args.solo else None
        generar(dia, h, c, salida, args.consejo, solo)
        return

    if not args.forzar or args.comprobar:
        ok, motivo, fin = toca_hoy(c, ahora, h, modo)
        if not ok:
            print(motivo)
            salida_github(toca="no")
            return
        if args.comprobar:
            print("Toca generar las historias de hoy")
            salida_github(toca="si")
            return
    else:
        _, _, fin = toca_hoy(c, ahora, h, modo)

    hoy = ahora.date()
    print("Descargando precios de surtidorbarato.es…")
    indice, por_provincia = datos.descargar_web()
    fecha_datos = datos.fecha_web(indice)
    if fecha_datos != hoy:
        print(f"Los datos son del {fecha_datos} y hoy es {hoy}: no se publica nada.")
        salida_github(toca="no")
        if ahora + dt.timedelta(minutes=35) >= fin:
            sys.exit("ERROR: se acabó el margen del día y el Ministerio no ha actualizado los datos.")
        return

    dia = datos.resumir(indice, por_provincia)
    hist.registrar_medias(h, dia["fecha"], {"95": dia["media95"], "diesel": dia["mediaDiesel"], "98": dia["media98"]}, "web")
    hist.dia(h, dia["fecha"])["barata"] = dia["barata"]
    completar_historico(h, hoy)

    print(f"Generando historias del {hoy} (modo {modo})…")
    historias, omitidas = generar(dia, h, c, salida)
    for o in omitidas:
        print(f"  ✗ No se genera {o}")
    d = hist.dia(h, dia["fecha"])
    d["estado"] = d.get("estado") if d.get("estado") == "publicado" else "generado"
    d["generadas"] = [x["clave"] for x in historias]
    hist.guardar(h)
    salida_github(toca="si" if historias else "no", fecha=dia["fecha"])


if __name__ == "__main__":
    main()
