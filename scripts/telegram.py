"""Envía por Telegram las historias del día (como archivos, sin pérdida de calidad).

Variables: TELEGRAM_TOKEN (secreto de GitHub, el que da @BotFather).
El chat al que se envía se descubre solo la primera vez (hay que haber pulsado
«Iniciar» en el chat del bot) y se guarda en recursos/telegram_chat.txt.
El identificador del chat no es secreto: sin el token no sirve para nada.
"""
import json
import os
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CHAT = RAIZ / "recursos" / "telegram_chat.txt"
API = "https://api.telegram.org/bot{token}/{metodo}"


def llamar(token, metodo, **kw):
    r = requests.post(API.format(token=token, metodo=metodo), timeout=120, **kw)
    datos = r.json()
    if not datos.get("ok"):
        # nunca se imprime el token
        raise SystemExit(f"ERROR de Telegram en {metodo}: {datos.get('description')}")
    return datos["result"]


def chat_id(token):
    if RUTA_CHAT.exists() and RUTA_CHAT.read_text().strip():
        return RUTA_CHAT.read_text().strip()
    for upd in reversed(llamar(token, "getUpdates")):
        chat = (upd.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            RUTA_CHAT.write_text(str(chat["id"]) + "\n")
            print(f"Chat de Telegram encontrado y guardado ({chat.get('first_name', '')})")
            return str(chat["id"])
    raise SystemExit("ERROR: no encuentro tu chat. Abre el chat de tu bot en Telegram, "
                     "pulsa «Iniciar» y vuelve a lanzar el workflow.")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("No hay TELEGRAM_TOKEN: no se envía nada por Telegram.")
        return
    fecha = os.environ.get("FECHA") or sys.argv[1]
    carpeta = RAIZ / "publico" / fecha
    manifest = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
    historias = manifest["historias"]
    destino = chat_id(token)

    d = fecha.split("-")
    texto = (f"Historias del {d[2]}/{d[1]}/{d[0]} ({len(historias)}), en orden de publicación.\n"
             "Guárdalas en la galería y súbelas en este orden.")
    if manifest.get("omitidas"):
        texto += "\n\nNo generadas hoy:\n" + "\n".join(f"• {o}" for o in manifest["omitidas"])
    llamar(token, "sendMessage", data={"chat_id": destino, "text": texto})

    # Como documentos (calidad original), en grupos de hasta 10
    for i in range(0, len(historias), 10):
        grupo = historias[i:i + 10]
        archivos, media = {}, []
        for n, x in enumerate(grupo):
            clave = f"f{n}"
            archivos[clave] = (x["png"], open(carpeta / x["png"], "rb"), "image/png")
            media.append({"type": "document", "media": f"attach://{clave}"})
        if len(grupo) == 1:
            llamar(token, "sendDocument", data={"chat_id": destino},
                   files={"document": archivos["f0"]})
        else:
            llamar(token, "sendMediaGroup", data={"chat_id": destino, "media": json.dumps(media)},
                   files=archivos)
    print(f"Enviadas {len(historias)} historias por Telegram")


if __name__ == "__main__":
    main()
