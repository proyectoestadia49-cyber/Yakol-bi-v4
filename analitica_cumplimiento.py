"""
analitica_cumplimiento.py -- Modulos analiticos de cumplimiento normativo
------------------------------------------------------------------------------
Todos estos analisis parten de los valores OFICIALES ya extraidos (nunca
recalculados): IGC/LIMRA por asesor (Fact_IGC, Fact_LIMRA), IGC/LIMRA del
promotor y bonos oficiales (Resumen_Bonos), y el detalle de Conexion y
Desarrollo por asesor (Historico_ConexionDesarrollo). El sistema calcula
ANALISIS sobre esos datos -- nunca sustituye el dato oficial.
"""

from datetime import date

import pandas as pd

from config import UMBRAL_IGC, UMBRAL_LIMRA, RAMPA_IGC_MESES, RAMPA_LIMRA_MESES, IDS_ASESOR_EXCLUIDOS


def _meses_antiguedad(fecha_ingreso_str, fecha_referencia):
    if not fecha_ingreso_str or fecha_referencia is None:
        return None
    for sep in ("-", "/"):
        partes = str(fecha_ingreso_str).split(sep)
        if len(partes) == 3:
            try:
                d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
                return (fecha_referencia.year - a) * 12 + (fecha_referencia.month - m)
            except ValueError:
                continue
    return None


def _fecha_referencia_de_periodo(id_periodo):
    s = str(id_periodo)
    if len(s) != 6:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), 1)
    except ValueError:
        return None


def calcular_comparativo_incumplimientos(fact_igc: pd.DataFrame, fact_limra: pd.DataFrame,
                                          dim_asesor: pd.DataFrame) -> pd.DataFrame:
    """Cruza el IGC/LIMRA oficial de cada asesor contra los umbrales
    normativos, aplicando la rampa de proteccion segun antiguedad. Los
    valores de IGC/LIMRA nunca se modifican -- solo se interpretan."""
    if fact_igc is None or fact_igc.empty:
        return pd.DataFrame()
    comp = fact_igc.merge(fact_limra, on=["ID_Asesor", "ID_Periodo"], how="outer") \
        if fact_limra is not None and not fact_limra.empty else fact_igc.copy()
    comp = comp[~comp["ID_Asesor"].astype(str).isin(IDS_ASESOR_EXCLUIDOS)]
    if "LIMRA_Indice_Real" not in comp.columns:
        comp["LIMRA_Indice_Real"] = None
    comp = comp.merge(dim_asesor[["ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso"]], on="ID_Asesor", how="left")
    comp["Fecha_Referencia_Periodo"] = comp["ID_Periodo"].apply(_fecha_referencia_de_periodo)
    comp["Meses_Antiguedad"] = comp.apply(
        lambda r: _meses_antiguedad(r["Fecha_Ingreso"], r["Fecha_Referencia_Periodo"]), axis=1)
    comp["En_Rampa_IGC"] = comp["Meses_Antiguedad"].apply(lambda m: m is not None and m <= RAMPA_IGC_MESES)
    comp["En_Rampa_LIMRA"] = comp["Meses_Antiguedad"].apply(lambda m: m is not None and m <= RAMPA_LIMRA_MESES)
    comp["Cumple_IGC"] = comp["IGC_Indice_Real"].apply(lambda v: None if pd.isna(v) else v >= UMBRAL_IGC)
    comp["Cumple_LIMRA"] = comp["LIMRA_Indice_Real"].apply(lambda v: None if pd.isna(v) else v >= UMBRAL_LIMRA)
    comp["Incumple_Real_IGC"] = comp.apply(lambda r: (r["Cumple_IGC"] is False) and (not r["En_Rampa_IGC"]), axis=1)
    comp["Incumple_Real_LIMRA"] = comp.apply(lambda r: (r["Cumple_LIMRA"] is False) and (not r["En_Rampa_LIMRA"]), axis=1)
    return comp.sort_values(["ID_Periodo", "ID_Asesor"]).reset_index(drop=True)


def calcular_seguimiento_igc(fact_igc: pd.DataFrame) -> pd.DataFrame:
    """Historico simple de IGC por asesor y periodo, con la variacion mes a
    mes -- pura lectura de tendencia sobre el dato oficial, sin modificarlo."""
    if fact_igc is None or fact_igc.empty:
        return pd.DataFrame()
    df = fact_igc.sort_values(["ID_Asesor", "ID_Periodo"]).copy()
    df["IGC_Variacion_vs_Mes_Anterior"] = df.groupby("ID_Asesor")["IGC_Indice_Real"].diff().round(2)
    return df


def calcular_seguimiento_limra(fact_limra: pd.DataFrame) -> pd.DataFrame:
    if fact_limra is None or fact_limra.empty:
        return pd.DataFrame()
    df = fact_limra.sort_values(["ID_Asesor", "ID_Periodo"]).copy()
    df["LIMRA_Variacion_vs_Mes_Anterior"] = df.groupby("ID_Asesor")["LIMRA_Indice_Real"].diff().round(2)
    return df


def calcular_seguimiento_bonos(resumen_bonos: pd.DataFrame) -> pd.DataFrame:
    """Tendencia mes a mes de cada concepto de bono oficial del promotor --
    util para detectar caidas como la que ya se identifico en el Bono de
    Desarrollo (de $9,000-$15,000 a $0 a partir de marzo). No recalcula
    ningun monto, solo compara los ya oficiales entre periodos."""
    if resumen_bonos is None or resumen_bonos.empty:
        return pd.DataFrame()
    df = resumen_bonos.sort_values("ID_Periodo").copy()
    columnas_bono = ["Bono_Vida", "Bono_GMMI", "Bono_Beneficios", "Subsidio_Renta",
                      "Bono_Conexion", "Bono_Desarrollo", "Bono_Crecimiento", "Bono_Total"]
    for col in columnas_bono:
        if col in df.columns:
            df[f"{col}_Variacion"] = df[col].diff().round(2)
    return df


def validar_conexion_desarrollo_entre_fuentes(historico_conexion_desarrollo: pd.DataFrame,
                                               resumen_bonos: pd.DataFrame) -> pd.DataFrame:
    """Cruza DOS fuentes oficiales entre si (nunca una formula propia): la
    suma del detalle por asesor del reporte 'Conexion y Desarrollo' contra
    el 'Bono_Desarrollo' + 'Bono_Conexion' del promotor en Resumen_Bonos.
    Esto detecta inconsistencias ENTRE los propios reportes de SMNYL, no
    errores del sistema."""
    if historico_conexion_desarrollo is None or historico_conexion_desarrollo.empty:
        return pd.DataFrame()
    suma_por_periodo = historico_conexion_desarrollo.groupby("ID_Periodo")["Bono_A_Pagar"].sum().reset_index()
    suma_por_periodo = suma_por_periodo.rename(columns={"Bono_A_Pagar": "Suma_Detalle_Por_Asesor"})
    if resumen_bonos is None or resumen_bonos.empty:
        suma_por_periodo["Bono_Promotor_Conexion_Mas_Desarrollo"] = None
        suma_por_periodo["Diferencia"] = None
        suma_por_periodo["Coincide"] = "Sin Resumen_Bonos para comparar"
        return suma_por_periodo
    resumen = resumen_bonos.copy()
    resumen["Bono_Promotor_Conexion_Mas_Desarrollo"] = resumen["Bono_Conexion"].fillna(0) + resumen["Bono_Desarrollo"].fillna(0)
    comparativo = suma_por_periodo.merge(
        resumen[["ID_Periodo", "Bono_Promotor_Conexion_Mas_Desarrollo"]], on="ID_Periodo", how="outer")
    comparativo["Diferencia"] = comparativo["Suma_Detalle_Por_Asesor"] - comparativo["Bono_Promotor_Conexion_Mas_Desarrollo"]
    comparativo["Coincide"] = comparativo["Diferencia"].abs() < 1.0
    return comparativo
