"""Publica en Instagram, como historias y en orden, las imágenes de publico/AAAA-MM-DD/.

Usa la API de Instagram con inicio de sesión de Instagram:
  1. POST /{IG_USER_ID}/media  (image_url, media_type=STORIES)  -> contenedor
  2. GET  /{contenedor}?fields=status_code  hasta FINISHED
  3. POST /{IG_USER_ID}/media_publish (creation_id)
Instagram solo acepta JPEG y descarga la imagen de una URL pública
(GitHub Pages), por eso se publica la copia .jpg.

Variables de entorno: IG_TOKEN (secreto), IG_USER_ID, BASE_URL (URL de GitHub Pages).
Cada historia publicada se apunta en historico.json: si el workflow se repite,
no se publica dos veces la misma.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import historico as hist  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class ErrorInstagram(Exception):
    pass


def api(metodo, ruta, cfg, **params):
    url = f"{cfg['host']}/{cfg['version']}/{ruta}"
    params["access_token"] = os.environ["IG_TOKEN"]
    r = requests.request(metodo, url, params=params if metodo == "GET" else None,
                         data=params if metodo == "POST" else None, timeout=60)
    datos = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in datos:
        err = datos.get("error", {})
        # Nunca se imprime el token
        raise ErrorInstagram(f"{ruta}: {err.get('message', r.status_code)} (código {err.get('code')})")
    return datos


def esperar_url(url, intentos=30):
    """GitHub Pages puede tardar en servir el despliegue recién hecho."""
    for _ in range(intentos):
        try:
            if requests.head(url, timeout=20).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(10)
    raise ErrorInstagram(f"La imagen no está accesible en {url}")


def publicar_historia(url_imagen, user_id, cfg):
    cont = api("POST", f"{user_id}/media", cfg, image_url=url_imagen, media_type="STORIES")["id"]
    for _ in range(30):
        estado = api("GET", cont, cfg, fields="status_code").get("status_code")
        if estado == "FINISHED":
            break
        if estado in ("ERROR", "EXPIRED"):
            raise ErrorInstagram(f"Instagram no pudo procesar la imagen ({estado})")
        time.sleep(5)
    else:
        raise ErrorInstagram("Instagram tardó demasiado en procesar la imagen")
    return api("POST", f"{user_id}/media_publish", cfg, creation_id=cont)["id"]


def main():
    cfg = yaml.safe_load((RAIZ / "config.yml").read_text(encoding="utf-8"))["instagram"]
    fecha = os.environ.get("FECHA") or sys.argv[1]
    base = os.environ["BASE_URL"].rstrip("/")
    user_id = os.environ["IG_USER_ID"]
    local = RAIZ / "publico" / fecha / "manifest.json"
    if local.exists():
        manifest = json.loads(local.read_text(encoding="utf-8"))
    else:  # en GitHub Actions las imágenes ya están en GitHub Pages
        esperar_url(f"{base}/{fecha}/manifest.json")
        manifest = requests.get(f"{base}/{fecha}/manifest.json", timeout=30).json()

    h = hist.cargar()
    d = hist.dia(h, fecha)
    hechas = set(d.get("publicadas", []))
    pendientes = [x for x in manifest["historias"] if x["clave"] not in hechas]
    print(f"{len(pendientes)} historias por publicar ({len(hechas)} ya publicadas)")

    errores = []
    for x in pendientes:
        url = f"{base}/{fecha}/{x['jpg']}"
        try:
            esperar_url(url)
            media_id = publicar_historia(url, user_id, cfg)
            d.setdefault("publicadas", []).append(x["clave"])
            hist.guardar(h)  # se guarda tras cada una por si falla la siguiente
            print(f"  ✓ {x['clave']} publicada ({media_id})")
            time.sleep(3)
        except ErrorInstagram as e:
            errores.append(f"{x['clave']}: {e}")
            print(f"  ✗ {x['clave']}: {e}")
            break  # se para para no desordenar la secuencia; el siguiente intento sigue por aquí

    if not errores and set(d.get("publicadas", [])) >= {x["clave"] for x in manifest["historias"]}:
        d["estado"] = "publicado"
        hist.guardar(h)
    if errores:
        sys.exit("ERROR al publicar en Instagram:\n" + "\n".join(errores))


if __name__ == "__main__":
    main()
