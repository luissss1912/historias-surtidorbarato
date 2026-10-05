"""Comprueba el token de Instagram: que funciona y que no está cerca de caducar.

Variables: IG_TOKEN (secreto), IG_TOKEN_CADUCA (variable del repositorio, AAAA-MM-DD,
la fecha en que caduca el token; los de larga duración duran 60 días).
Si falla, el job falla y GitHub manda un correo. No afecta a la publicación del día.
"""
import datetime as dt
import os
import sys
from pathlib import Path

import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
cfg = yaml.safe_load((RAIZ / "config.yml").read_text(encoding="utf-8"))["instagram"]

token = os.environ.get("IG_TOKEN")
if not token:
    print("Todavía no hay token de Instagram (secreto IG_TOKEN). Nada que comprobar.")
    sys.exit(0)

r = requests.get(f"{cfg['host']}/{cfg['version']}/me", params={"fields": "user_id,username", "access_token": token}, timeout=30)
if r.status_code != 200:
    sys.exit(f"ERROR: el token de Instagram no funciona ({r.json().get('error', {}).get('message', r.status_code)}). "
             "Genera uno nuevo y actualiza el secreto IG_TOKEN.")
print(f"Token válido para @{r.json().get('username')}")

caduca = os.environ.get("IG_TOKEN_CADUCA")
if not caduca:
    print("Aviso: falta la variable IG_TOKEN_CADUCA; no se puede avisar antes de que caduque.")
    sys.exit(0)
quedan = (dt.date.fromisoformat(caduca) - dt.date.today()).days
print(f"El token caduca el {caduca} (quedan {quedan} días)")
if quedan <= cfg["aviso_token_dias"]:
    sys.exit(f"AVISO: el token de Instagram caduca en {quedan} días ({caduca}). "
             "Renuévalo y actualiza el secreto IG_TOKEN y la variable IG_TOKEN_CADUCA.")
