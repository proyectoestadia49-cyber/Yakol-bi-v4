"""
log_procesamiento.py -- Trazabilidad del proceso
-----------------------------------------------------
Construye un renglon de auditoria por cada corrida del sistema: que ZIP se
proceso, cuando, que se encontro, que fallo. Se acumula igual que el resto
del Excel Maestro (nunca se pierde el historial de corridas anteriores).
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class RegistroLog:
    nombre_zip: str
    id_periodo: str | None
    pdfs_encontrados: int
    tipos_encontrados: list = field(default_factory=list)
    tipos_faltantes: list = field(default_factory=list)
    registros_importados: int = 0
    registros_actualizados: int = 0
    advertencias: list = field(default_factory=list)
    errores: list = field(default_factory=list)

    def a_fila(self) -> dict:
        return {
            "Fecha_Hora": datetime.now().isoformat(timespec="seconds"),
            "Nombre_ZIP": self.nombre_zip,
            "ID_Periodo_Detectado": self.id_periodo or "NO DETECTADO",
            "PDFs_Encontrados": self.pdfs_encontrados,
            "Tipos_Encontrados": ", ".join(self.tipos_encontrados),
            "Tipos_Faltantes": ", ".join(self.tipos_faltantes) if self.tipos_faltantes else "Ninguno",
            "Registros_Importados": self.registros_importados,
            "Registros_Actualizados": self.registros_actualizados,
            "Advertencias": " | ".join(self.advertencias) if self.advertencias else "Ninguna",
            "Errores": " | ".join(self.errores) if self.errores else "Ninguno",
        }


def construir_log(registro: RegistroLog, log_historico: pd.DataFrame | None) -> pd.DataFrame:
    fila_nueva = pd.DataFrame([registro.a_fila()])
    if log_historico is None or log_historico.empty:
        return fila_nueva
    return pd.concat([log_historico, fila_nueva], ignore_index=True)
