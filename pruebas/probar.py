"""Pruebas sin red: cálculo de cifras (comparado con lo que muestra la web) y
recorrido completo de varios días (rotación, histórico, miércoles y domingo).
Uso: python pruebas/probar.py
"""
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import datos  # noqa: E402

# Filas reales de surtidorbarato.es (05/10/2026) de Ceuta y Melilla, columnas recortadas
def fila(i, marca, mun, prov, p95, pd, p98):
    return [i, marca, "", mun, "", prov, "", 0, 0, "", p95, pd, p98]

CEUTA = [fila(2901, "Shell Catena", "Ceuta", "51", 1.623, 1.748, 1.653), fila(2755, "Shell Punta Almina", "Ceuta", "51", 1.623, 1.748, 1.653),
         fila(8908, "Shell Muelle Dato", "Ceuta", "51", 1.623, 1.748, 1.623), fila(11303, "Cepsa", "Ceuta", "51", 1.624, 1.734, 0),
         fila(2754, "Cepsa", "Ceuta", "51", 1.624, 1.734, 0), fila(16166, "Moeve", "Ceuta", "51", 1.624, 1.749, 1.654),
         fila(11739, "On365", "Ceuta", "51", 1.604, 1.729, 1.634), fila(10513, "Disa Varadero", "Ceuta", "51", 1.623, 1.748, 1.653),
         fila(2900, "Disa Puerto", "Ceuta", "51", 1.623, 1.748, 1.653), fila(2903, "On365", "Ceuta", "51", 1.604, 1.729, 1.634)]
MELILLA = [fila(16331, "Bp Melilla Puerto", "Melilla", "52", 1.584, 1.565, 0), fila(10325, "Shell", "Melilla", "52", 1.584, 1.567, 0),
           fila(10279, "Shell Alfonso Xiii", "Melilla", "52", 1.584, 1.567, 0), fila(10281, "Shell Puente Triana", "Melilla", "52", 1.584, 1.567, 0),
           fila(10280, "Shell Carlos V", "Melilla", "52", 1.584, 1.567, 0), fila(2749, "BP", "Melilla", "52", 1.574, 1.555, 0),
           fila(8765, "Shell", "Melilla", "52", 1.584, 1.567, 0), fila(10324, "Shell", "Melilla", "52", 1.584, 1.567, 0),
           fila(2747, "Moeve", "Melilla", "52", 1.584, 1.567, 0), fila(2744, "Moeve", "Melilla", "52", 1.584, 1.567, 0),
           fila(2746, "Bp Poligono", "Melilla", "52", 1.574, 1.555, 0), fila(2748, "Bp Puente", "Melilla", "52", 1.585, 1.565, 0)]


def indice(fecha, codigos):
    nombres = {"51": "Ceuta", "52": "Melilla", "28": "Madrid", "08": "Barcelona", "46": "Valencia", "41": "Sevilla"}
    return {"fecha": {"iso": fecha, "isoCompleto": fecha + "T08:00:00+02:00"}, "version": "x",
            "provincias": [[c, nombres.get(c, c), [0, 0, 0, 0], 1, ""] for c in codigos]}


def prueba_calculos():
    d = datos.resumir(indice("2026-10-05", ["51", "52"]), {"51": CEUTA, "52": MELILLA})
    # Valores que muestra la web ese día (calculados con su mismo JavaScript)
    assert abs(d["provincias"]["51"]["media95"] - 1.6195) < 1e-9
    assert abs(d["provincias"]["52"]["media95"] - 1.5824166666666668) < 1e-9
    assert [x["id"] for x in d["provincias"]["51"]["top5"]] == [11739, 2903, 2901, 2755, 8908]
    assert [x["id"] for x in d["provincias"]["52"]["top5"]] == [2749, 2746, 16331, 10325, 10279]
    assert d["barata"] is None  # Ceuta y Melilla no cuentan para «la más barata de España»
    assert datos.limpiar_nombre("E.s.+Agricola+S.c.j.+de+Albal%2c+C.v.") == "E.s. Agricola S.c.j. de Albal, C.v."
    assert datos.limpiar_nombre("+B Energias") == "+B Energias"
    print("✓ cálculos iguales que en la web")


def prueba_semana():
    """Simula 15 días seguidos (de lunes a lunes) con datos sintéticos, sin publicar nada."""
    import generar
    import historico as hist
    import reel  # en la simulación no se renderiza el vídeo (tarda ~15 s por día)
    reel.generar_reel = lambda d, ruta: (ruta.write_bytes(b""), ruta.with_suffix(".png").write_bytes(b""))

    tmp = Path(tempfile.mkdtemp())
    hist.RUTA = tmp / "historico.json"
    base = []
    for i, c in enumerate(["28", "08", "46", "41", "51", "52"]):
        filas = CEUTA if c != "52" else MELILLA
        base.append((c, [[f[0] + 100000 * i, f[1], *f[2:5], c, *f[6:]] for f in filas]))

    hoy = {"f": None}
    datos.descargar_web = lambda: (indice(hoy["f"], [c for c, _ in base]), dict(base))
    datos.medias_ministerio = lambda f: (_ for _ in ()).throw(datos.DatosNoDisponibles("sin red"))

    rotatorias, extras = [], {}
    inicio = dt.date(2026, 10, 5)
    for n in range(15):
        f = inicio + dt.timedelta(days=n)
        hoy["f"] = f.isoformat()
        # cambia un poco los precios cada día
        for _, filas in base:
            for x in filas:
                x[10] = round(x[10] + (0.001 if n % 3 else -0.002), 3)
        h = hist.cargar()
        dia = datos.resumir(*datos.descargar_web())
        hist.registrar_medias(h, dia["fecha"], {"95": dia["media95"], "diesel": dia["mediaDiesel"], "98": dia["media98"]}, "web")
        dia["barata"] = dia["provincias"]["28"]["top5"][0]  # en la simulación no hay península
        historias, omitidas = generar.generar(dia, h, generar.cfg(), tmp / "publico")
        d = hist.dia(h, dia["fecha"])
        d["estado"] = "generado"
        hist.guardar(h)
        rotatorias.append(d["rotatoria"])
        claves = [x["clave"] for x in historias]
        if f.weekday() in (2, 6) or n in (0, 1):
            extras[f.isoformat()] = (claves, omitidas)

    for k, v in extras.items():
        print(" ", k, v)
    assert len(set(rotatorias)) == 15, "la provincia rotatoria no debe repetirse"
    assert rotatorias[0] == "15", "empieza por A Coruña"
    assert "A" not in extras["2026-10-05"][0], "el primer día no hay media de ayer"
    assert "A" in extras["2026-10-06"][0]
    assert "D" in extras["2026-10-07"][0] and "D" in extras["2026-10-14"][0]
    assert "E" not in extras["2026-10-11"][0], "el primer domingo no hay dos semanas de histórico"
    assert "E" in extras["2026-10-18"][0], "el segundo domingo ya hay resumen semanal"
    print("✓ rotación, histórico, miércoles y domingo")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    prueba_calculos()
    prueba_semana()
