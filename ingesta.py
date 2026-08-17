"""
ingesta.py -- Etapa 1: Carga de archivos
-------------------------------------------
Responsabilidad unica: recibir el ZIP mensual, descomprimirlo, y determinar
a que periodo (AAAAMM) corresponde. No abre ni interpreta PDFs -- eso es
responsabilidad de clasificador.py y extractores.py.
"""

import re
import zipfile
from pathlib import Path
from dataclasses import dataclass, field

from config import MESES_ES


@dataclass
class ResultadoIngesta:
    id_periodo: str | None
    pdfs_encontrados: list
    carpeta_extraido: str
    conteo_encontrado: int
    periodo_detectado_de: str  # "nombre_zip" o "no_detectado"
    errores: list = field(default_factory=list)


def detectar_periodo_de_nombre(nombre_archivo: str) -> str | None:
    """Busca un mes en espanol + un anio de 4 digitos en el nombre del ZIP.
    Regresa None si no lo encuentra -- la aplicacion debe entonces pedir
    confirmacion manual, nunca asumir un periodo por defecto."""
    nombre = nombre_archivo.upper()
    anio_match = re.search(r"(20\d{2})", nombre)
    mes_encontrado = next((i + 1 for i, mes in enumerate(MESES_ES) if mes in nombre), None)
    if anio_match and mes_encontrado:
        return f"{anio_match.group(1)}{mes_encontrado:02d}"
    return None


def ingestar_zip(ruta_zip: str, carpeta_trabajo: str, id_periodo_manual: str | None = None) -> ResultadoIngesta:
    """Descomprime el ZIP y arma el resultado de la etapa de ingesta.

    Si id_periodo_manual se proporciona, tiene prioridad sobre la deteccion
    automatica (permite que la interfaz ofrezca una confirmacion manual
    cuando el nombre del archivo no es reconocible).
    """
    ruta_zip = Path(ruta_zip)
    carpeta_extraido = Path(carpeta_trabajo) / ruta_zip.stem
    carpeta_extraido.mkdir(parents=True, exist_ok=True)
    errores = []

    try:
        with zipfile.ZipFile(ruta_zip, "r") as z:
            z.extractall(carpeta_extraido)
    except zipfile.BadZipFile:
        errores.append(f"El archivo '{ruta_zip.name}' no es un ZIP valido o esta corrupto.")
        return ResultadoIngesta(None, [], str(carpeta_extraido), 0, "error", errores)

    pdfs = sorted(str(p) for p in carpeta_extraido.rglob("*.pdf"))

    if id_periodo_manual:
        periodo, origen = id_periodo_manual, "confirmacion_manual"
    else:
        periodo = detectar_periodo_de_nombre(ruta_zip.name)
        origen = "nombre_zip" if periodo else "no_detectado"

    if not pdfs:
        errores.append(f"No se encontro ningun PDF dentro de '{ruta_zip.name}'.")

    return ResultadoIngesta(
        id_periodo=periodo, pdfs_encontrados=pdfs, carpeta_extraido=str(carpeta_extraido),
        conteo_encontrado=len(pdfs), periodo_detectado_de=origen, errores=errores,
    )
