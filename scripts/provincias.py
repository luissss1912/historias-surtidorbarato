"""Provincias de España por código INE (el campo IDProvincia del Ministerio)."""
import unicodedata

PROVINCIAS = {
    "01": "Araba", "02": "Albacete", "03": "Alicante", "04": "Almería",
    "05": "Ávila", "06": "Badajoz", "07": "Illes Balears", "08": "Barcelona",
    "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
    "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña", "16": "Cuenca",
    "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
    "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
    "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
    "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
    "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
    "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
    "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
    "52": "Melilla",
}

# Fuera de la península: Baleares, Canarias, Ceuta y Melilla
NO_PENINSULA = {"07", "35", "38", "51", "52"}


def clave_orden(nombre: str) -> str:
    """Orden alfabético español sin tener en cuenta tildes."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", nombre.lower())
        if unicodedata.category(c) != "Mn" or c == "\u0303"  # conserva la ñ
    )
    return sin_tildes.replace("n\u0303", "n~")  # ñ va después de n


def lista_rotatoria(fijas):
    """Todas las provincias menos las fijas, en orden alfabético."""
    codigos = [c for c in PROVINCIAS if c not in set(fijas)]
    return sorted(codigos, key=lambda c: clave_orden(PROVINCIAS[c]))


if __name__ == "__main__":
    for i, c in enumerate(lista_rotatoria(["28", "08", "46", "41"])):
        print(i, c, PROVINCIAS[c])
