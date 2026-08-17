"""
clasificador.py -- Etapa 2: Identificacion de los reportes PDF
-------------------------------------------------------------------
Responsabilidad unica: dado un PDF, decidir a cual de los tipos de reporte
conocidos corresponde, leyendo su contenido (nunca su nombre de archivo).
"""

from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from config import FIRMAS_REPORTES


@dataclass
class ResultadoClasificacion:
    ruta_pdf: str
    tipo: str | None

    @property
    def reconocido(self) -> bool:
        return self.tipo is not None

    def __repr__(self):
        return f"<{Path(self.ruta_pdf).name} -> {self.tipo or 'NO RECONOCIDO'}>"


def _texto_primera_pagina(ruta_pdf: str) -> str:
    with pdfplumber.open(ruta_pdf) as pdf:
        return (pdf.pages[0].extract_text() or "").upper()


def _coincide_firma(texto: str, firma: dict) -> bool:
    if not all(palabra.upper() in texto for palabra in firma["debe_contener"]):
        return False
    if any(palabra.upper() in texto for palabra in firma.get("no_debe_contener", [])):
        return False
    return True


def clasificar_pdf(ruta_pdf: str) -> ResultadoClasificacion:
    texto = _texto_primera_pagina(ruta_pdf)
    for firma in FIRMAS_REPORTES:
        if _coincide_firma(texto, firma):
            return ResultadoClasificacion(ruta_pdf, firma["tipo"])
    return ResultadoClasificacion(ruta_pdf, None)


def clasificar_lote(rutas_pdf: list) -> list:
    return [clasificar_pdf(r) for r in rutas_pdf]
