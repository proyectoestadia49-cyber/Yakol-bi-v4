"""
validaciones.py -- Etapa 7: Validaciones
--------------------------------------------
Corre una serie de comprobaciones automaticas ANTES de escribir el Excel
final. Si algo falla, se regresa una lista de problemas claros -- la
aplicacion decide si detener el proceso o continuar mostrando la
advertencia, pero nunca falla en silencio.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ResultadoValidacion:
    valido: bool
    errores: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)


def validar_todo(resumen_bonos: pd.DataFrame, historico_actividad: pd.DataFrame,
                  fact_igc: pd.DataFrame, fact_limra: pd.DataFrame,
                  id_periodo: str, conteo_asesores_actividad_esperado: int) -> ResultadoValidacion:
    errores, advertencias = [], []

    # 1. Sin registros duplicados de bonos (un solo renglon por promotor+periodo)
    sub_bonos = resumen_bonos[resumen_bonos["ID_Periodo"] == id_periodo]
    duplicados_bonos = sub_bonos.duplicated(subset=["ID_Promotor", "ID_Periodo"]).sum()
    if duplicados_bonos > 0:
        errores.append(f"Se encontraron {duplicados_bonos} registro(s) duplicados de bonos para el periodo {id_periodo}.")

    # 2. Sin asesores repetidos en el mismo periodo
    sub_act = historico_actividad[historico_actividad["ID_Periodo"] == id_periodo]
    duplicados_asesores = sub_act.duplicated(subset=["ID_Periodo", "ID_Asesor"]).sum()
    if duplicados_asesores > 0:
        errores.append(f"Se encontraron {duplicados_asesores} asesor(es) repetidos en el periodo {id_periodo}.")

    # 3. Montos numericos (no texto) en las columnas de bono
    columnas_monto = ["Bono_Vida", "Bono_GMMI", "Bono_Beneficios", "Subsidio_Renta",
                       "Bono_Conexion", "Bono_Desarrollo", "Bono_Crecimiento", "Bono_Total"]
    for col in columnas_monto:
        if col in sub_bonos.columns:
            no_numericos = sub_bonos[col].apply(lambda v: v is not None and not isinstance(v, (int, float))).sum()
            if no_numericos > 0:
                errores.append(f"La columna '{col}' contiene valores no numericos en el periodo {id_periodo}.")

    # 4. Bono Total coincide con el valor oficial (si se pudo extraer completo)
    if len(sub_bonos) and not sub_bonos["Bono_Total_Es_Oficial"].iloc[0]:
        advertencias.append(
            f"No se pudo confirmar el Bono Total oficial del PDF para el periodo {id_periodo} "
            "(el formato del resumen no coincidio con el patron esperado). Revisar manualmente."
        )

    # 5. Cantidad de asesores coincide entre Actividad y el resto de reportes
    n_asesores_actividad = sub_act["ID_Asesor"].nunique()
    if conteo_asesores_actividad_esperado and n_asesores_actividad != conteo_asesores_actividad_esperado:
        advertencias.append(
            f"El reporte de Actividad tiene {n_asesores_actividad} asesores, pero se esperaban "
            f"{conteo_asesores_actividad_esperado} segun otros reportes del mismo periodo. Puede ser normal "
            "(no todos los asesores generan actividad reportable), pero conviene revisarlo."
        )

    # 6. Sin periodos duplicados en las tablas historicas completas
    for nombre, tabla in [("Resumen_Bonos", resumen_bonos), ("Historico_Actividad", historico_actividad),
                           ("Fact_IGC", fact_igc), ("Fact_LIMRA", fact_limra)]:
        if tabla is not None and not tabla.empty:
            llave = ["ID_Promotor", "ID_Periodo"] if nombre == "Resumen_Bonos" else \
                    ["ID_Periodo", "ID_Asesor"]
            llave = [c for c in llave if c in tabla.columns]
            if llave and tabla.duplicated(subset=llave).any():
                errores.append(f"La tabla '{nombre}' tiene registros duplicados en la combinacion {llave}.")

    # 7. Checksum de validacion cruzada: el IGC/LIMRA del promotor (en
    # Resumen_Bonos) deberia ser cercano al promedio de los asesores del
    # mismo periodo. No son necesariamente identicos (el indice del
    # promotor puede ponderar distinto), pero una diferencia grande es
    # senal de un problema de lectura en alguno de los dos reportes.
    sub_resumen = resumen_bonos[resumen_bonos["ID_Periodo"] == id_periodo] if resumen_bonos is not None else pd.DataFrame()
    if len(sub_resumen) and fact_igc is not None and not fact_igc.empty:
        sub_fact_igc = fact_igc[fact_igc["ID_Periodo"] == id_periodo]
        if len(sub_fact_igc):
            promedio_igc_asesores = sub_fact_igc["IGC_Indice_Real"].mean()
            igc_promotor = sub_resumen["IGC"].iloc[0]
            if abs(igc_promotor - promedio_igc_asesores) > 15:
                advertencias.append(
                    f"El IGC del promotor ({igc_promotor:.2f}%) difiere en mas de 15 puntos del "
                    f"promedio simple de los asesores ({promedio_igc_asesores:.2f}%) para el periodo "
                    f"{id_periodo}. Puede ser normal (el indice del promotor pondera por prima, no es "
                    "un promedio simple), pero conviene revisar si hubo un error de lectura."
                )

    return ResultadoValidacion(valido=(len(errores) == 0), errores=errores, advertencias=advertencias)
