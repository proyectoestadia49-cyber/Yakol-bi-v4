"""
transformacion.py -- Etapas 4 y 5: Limpieza/transformacion y consolidacion historica
----------------------------------------------------------------------------------------
Aqui vive toda la logica que garantiza que el Excel Maestro no tenga
duplicados: cada asesor aparece una sola vez por periodo, cada promotor
aparece una sola vez por periodo, y cada bono del promotor aparece una
sola vez por periodo (nunca repetido por cada asesor).
"""

from datetime import date

import pandas as pd

from config import (
    COLUMNAS_DIM_ASESOR, COLUMNAS_DIM_PROMOTOR, COLUMNAS_DIM_PERIODO,
    COLUMNAS_HISTORICO_ACTIVIDAD, COLUMNAS_RESUMEN_BONOS, MESES_ES,
    COLUMNAS_HISTORICO_GMM, COLUMNAS_HISTORICO_TRASPASOS, COLUMNAS_HISTORICO_CONEXION_DESARROLLO,
)


def construir_historico_gmm(tabla_gmm: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_gmm is None or tabla_gmm.empty:
        return pd.DataFrame(columns=COLUMNAS_HISTORICO_GMM)
    df = tabla_gmm.copy()
    df["ID_Periodo"] = id_periodo
    df = df.groupby(["ID_Periodo", "ID_Asesor"], as_index=False).agg({
        "Primas_Iniciales_Mes": "sum", "Primas_Renovacion_Mes": "sum", "Polizas_Mes": "sum",
    })
    return df[COLUMNAS_HISTORICO_GMM]


def construir_historico_traspasos(tabla_traspasos: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_traspasos is None or tabla_traspasos.empty:
        return pd.DataFrame(columns=COLUMNAS_HISTORICO_TRASPASOS)
    df = tabla_traspasos.copy()
    df["ID_Periodo"] = id_periodo
    df = df.reset_index(drop=True)
    df["ID_Registro"] = df["ID_Periodo"] + "-" + df.index.astype(str)
    return df[COLUMNAS_HISTORICO_TRASPASOS]


def construir_historico_conexion_desarrollo(tabla_cd: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_cd is None or tabla_cd.empty:
        return pd.DataFrame(columns=COLUMNAS_HISTORICO_CONEXION_DESARROLLO)
    df = tabla_cd.copy()
    df["ID_Periodo"] = id_periodo
    df = df.drop_duplicates(subset=["ID_Periodo", "ID_Asesor", "Mes_Num"], keep="first")
    return df[COLUMNAS_HISTORICO_CONEXION_DESARROLLO]


# ---------------------------------------------------------------------------
# Construccion de dimensiones
# ---------------------------------------------------------------------------

def construir_dim_periodo(id_periodo: str) -> pd.DataFrame:
    anio, mes = int(id_periodo[:4]), int(id_periodo[4:6])
    return pd.DataFrame([{
        "ID_Periodo": id_periodo, "Anio": anio, "Mes": mes,
        "Nombre_Mes": MESES_ES[mes - 1].capitalize(),
    }])


def construir_dim_asesor(tabla_igc: pd.DataFrame, tabla_limra: pd.DataFrame, tabla_gmm: pd.DataFrame) -> pd.DataFrame:
    """Consolida el catalogo de asesores a partir de los tres reportes que
    los mencionan, eliminando duplicados por ID_Asesor (se conserva el
    primer nombre/fecha de ingreso encontrado, que en la practica es
    identico entre reportes de un mismo asesor)."""
    frames = []
    for tabla in (tabla_igc, tabla_limra, tabla_gmm):
        if tabla is not None and not tabla.empty and "ID_Asesor" in tabla.columns:
            cols = [c for c in COLUMNAS_DIM_ASESOR if c in tabla.columns]
            frames.append(tabla[cols])
    if not frames:
        return pd.DataFrame(columns=COLUMNAS_DIM_ASESOR)
    consolidado = pd.concat(frames, ignore_index=True)
    consolidado = consolidado.drop_duplicates(subset=["ID_Asesor"], keep="first")
    return consolidado.sort_values("ID_Asesor").reset_index(drop=True)


def construir_dim_promotor(id_promotor: str, nombre_promotor: str) -> pd.DataFrame:
    return pd.DataFrame([{"ID_Promotor": id_promotor, "Nombre_Promotor": nombre_promotor}])


# ---------------------------------------------------------------------------
# Construccion de hechos (Fact_IGC, Fact_LIMRA)
# ---------------------------------------------------------------------------

def construir_fact_igc(tabla_igc: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_igc is None or tabla_igc.empty:
        return pd.DataFrame(columns=COLUMNAS_FACT_IGC_CONST)
    df = tabla_igc[["ID_Asesor", "IGC_Indice_Real"]].copy()
    df["ID_Periodo"] = id_periodo
    df = df.drop_duplicates(subset=["ID_Asesor", "ID_Periodo"], keep="first")
    return df[["ID_Asesor", "ID_Periodo", "IGC_Indice_Real"]]


def construir_fact_limra(tabla_limra: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_limra is None or tabla_limra.empty:
        return pd.DataFrame(columns=COLUMNAS_FACT_LIMRA_CONST)
    df = tabla_limra[["ID_Asesor", "LIMRA_Indice_Real"]].copy()
    df["ID_Periodo"] = id_periodo
    df = df.drop_duplicates(subset=["ID_Asesor", "ID_Periodo"], keep="first")
    return df[["ID_Asesor", "ID_Periodo", "LIMRA_Indice_Real"]]


COLUMNAS_FACT_IGC_CONST = ["ID_Asesor", "ID_Periodo", "IGC_Indice_Real"]
COLUMNAS_FACT_LIMRA_CONST = ["ID_Asesor", "ID_Periodo", "LIMRA_Indice_Real"]


# ---------------------------------------------------------------------------
# Historico_Actividad -- consolidado por Periodo + ID_Asesor (unico)
# ---------------------------------------------------------------------------

def construir_historico_actividad(tabla_actividad: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if tabla_actividad is None or tabla_actividad.empty:
        return pd.DataFrame(columns=COLUMNAS_HISTORICO_ACTIVIDAD)
    df = tabla_actividad.copy()
    df["ID_Periodo"] = id_periodo
    # Consolidacion por asesor: si el mismo asesor aparece mas de una vez en
    # el mismo periodo (no deberia pasar, pero se protege explicitamente),
    # se conserva un solo renglon, sumando las metricas numericas.
    columnas_numericas = ["Polizas_Vida", "Polizas_GMMI", "Produccion_Total_Semestral", "Bono_Por_Asesor"]
    agregaciones = {c: "sum" for c in columnas_numericas}
    agregaciones.update({"Nombre_Asesor": "first", "Fecha_Concurso": "first", "ID_Promotor": "first"})
    df = df.groupby(["ID_Periodo", "ID_Asesor"], as_index=False).agg(agregaciones)
    return df[COLUMNAS_HISTORICO_ACTIVIDAD]


# ---------------------------------------------------------------------------
# Resumen_Bonos -- UN renglon por Promotor + Periodo, nunca por asesor
# ---------------------------------------------------------------------------

def construir_resumen_bonos(datos_bonos_promotor: dict, id_periodo: str) -> pd.DataFrame:
    """datos_bonos_promotor viene de extractores.extraer_bonos_promotores(),
    que ya regresa un solo diccionario (un solo promotor). Aqui simplemente
    se le agrega el periodo y se arma como DataFrame de un renglon -- por
    diseno, es fisicamente imposible que este paso genere duplicados por
    asesor, porque nunca recibe informacion a nivel asesor."""
    fila = {
        "ID_Periodo": id_periodo,
        "ID_Promotor": datos_bonos_promotor["ID_Promotor"],
        "IGC": datos_bonos_promotor.get("IGC"),
        "LIMRA": datos_bonos_promotor.get("LIMRA"),
        "Bono_Vida": datos_bonos_promotor.get("Bono_Vida"),
        "Bono_GMMI": datos_bonos_promotor.get("Bono_GMMI"),
        "Bono_Beneficios": datos_bonos_promotor.get("Bono_Beneficios"),
        "Subsidio_Renta": datos_bonos_promotor.get("Subsidio_Renta"),
        "Bono_Conexion": datos_bonos_promotor.get("Bono_Conexion"),
        "Bono_Desarrollo": datos_bonos_promotor.get("Bono_Desarrollo"),
        "Bono_Crecimiento": datos_bonos_promotor.get("Bono_Crecimiento"),
        "Bono_Total": datos_bonos_promotor.get("Bono_Total"),
        "Bono_Total_Es_Oficial": datos_bonos_promotor.get("Bono_Total_Es_Oficial", False),
    }
    return pd.DataFrame([fila])[COLUMNAS_RESUMEN_BONOS]


# ---------------------------------------------------------------------------
# Acumulacion historica: reemplaza el periodo si ya existia, agrega si es
# nuevo. Nunca duplica un periodo ya presente.
# ---------------------------------------------------------------------------

def fusionar_periodo(tabla_historica: pd.DataFrame, tabla_nueva: pd.DataFrame,
                      id_periodo: str, columna_periodo: str = "ID_Periodo") -> pd.DataFrame:
    if tabla_historica is None or tabla_historica.empty:
        return tabla_nueva.copy()
    historico_sin_este_periodo = tabla_historica[tabla_historica[columna_periodo].astype(str) != str(id_periodo)]
    combinado = pd.concat([historico_sin_este_periodo, tabla_nueva], ignore_index=True, sort=False)
    return combinado


def fusionar_dim_asesor(dim_historico: pd.DataFrame, dim_nuevo: pd.DataFrame) -> pd.DataFrame:
    """Las dimensiones no se reemplazan por periodo -- se combinan y se
    deduplica por ID_Asesor, quedandose con el registro mas reciente."""
    if dim_historico is None or dim_historico.empty:
        return dim_nuevo.copy()
    combinado = pd.concat([dim_historico, dim_nuevo], ignore_index=True)
    return combinado.drop_duplicates(subset=["ID_Asesor"], keep="last").sort_values("ID_Asesor").reset_index(drop=True)
