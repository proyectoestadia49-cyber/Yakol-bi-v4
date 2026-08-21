"""
analitica_avanzada.py -- Modulos analiticos financieros y estadisticos
-----------------------------------------------------------------------------
Segmentacion de asesores, costeo de reclutamiento, ROI de campanas, Real vs
Plan, analisis de sensibilidad, y simulacion Monte Carlo -- todos construidos
sobre los datos oficiales ya consolidados (IGC/LIMRA/produccion/bonos),
nunca recalculando los montos de bono, solo analizandolos.
"""

from datetime import date

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from config import (
    META_ANUAL_POLIZAS_VIDA, META_ANUAL_ASESORES_NUEVOS,
    PESOS_INDICE_SALUD, PUNTAJE_POR_NIVEL, BANDAS_LECTURA_MENSUAL,
    PRESUPUESTO_YAKOL, calcular_presupuesto_mensualizado, NUMERO_FUNCIONES_PROMOTORIA,
)


# ---------------------------------------------------------------------------
# Indice de Salud del Negocio -- reemplaza la segmentacion por KMeans.
#
# Diferencia clave con el metodo anterior: KMeans agrupaba a los asesores
# de forma RELATIVA al resto del grupo de ese mismo mes (el mismo asesor
# podia caer en "riesgo" o "alto desempeno" segun quien mas estuviera en la
# muestra ese periodo). Este metodo usa bandas FIJAS, tomadas del documento
# oficial de la promotoria -- el mismo desempeno siempre produce la misma
# clasificacion, sin importar el resto del grupo ese mes.
#
# Nota de transparencia metodologica: dos de las seis variables (Polizas
# GMM y Prima GMM) tienen bandas ambiguas en el documento fuente -- los
# niveles "Promedio", "Proactivo" y "Riesgo Medio" comparten el mismo rango
# para GMM (ej. los tres dicen "1 poliza"). Ante esa ambiguedad, se opto
# por la interpretacion MENOS punitiva en cada caso, para evitar falsos
# positivos de riesgo -- exactamente la preocupacion que senalo Gerardo.
# ---------------------------------------------------------------------------

def _nivel_polizas_vida(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 5:
        return "Extraordinario"
    if v == 4:
        return "Bueno"
    if v == 3:
        return "Promedio"
    if v >= 1:
        return "Proactivo"
    return "Riesgo Medio"  # 0 polizas Vida -- ambiguo con Riesgo Alto, se usa el menos punitivo


def _nivel_prima_vida(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 150000:
        return "Extraordinario"
    if v >= 120000:
        return "Bueno"
    if v >= 90000:
        return "Promedio"
    if v >= 30000:
        return "Proactivo"
    return "Riesgo Medio"  # 0-29,999 -- ambiguo con Riesgo Alto, se usa el menos punitivo


def _nivel_polizas_gmm(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 3:
        return "Extraordinario"
    if v == 2:
        return "Bueno"
    if v >= 1:
        return "Promedio"  # 1 poliza -- ambiguo entre Promedio/Proactivo/Riesgo Medio, se usa el intermedio
    return "Riesgo Alto"  # 0 -- este si es inequivoco


def _nivel_prima_gmm(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 90000:
        return "Extraordinario"
    if v >= 60000:
        return "Bueno"
    if v >= 30000:
        return "Promedio"
    return "Proactivo"  # 0-29,999 -- ambiguo con Riesgo Medio, se usa el menos punitivo


def _nivel_limra(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 95.5:
        return "Extraordinario"
    if v >= 91.5:
        return "Bueno"
    if v >= 89.5:
        return "Promedio"
    if v >= 87.5:
        return "Proactivo"
    if v >= 84.5:
        return "Riesgo Medio"
    return "Riesgo Alto"


def _nivel_igc(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if v >= 95.75:
        return "Extraordinario"
    if v >= 95:
        return "Bueno"
    if v >= 92.5:
        return "Promedio"
    if v >= 91.5:
        return "Proactivo"
    if v >= 91:
        return "Riesgo Medio"
    return "Riesgo Alto"


def _lectura_final(indice):
    for minimo, maximo, etiqueta in BANDAS_LECTURA_MENSUAL:
        if minimo <= indice < maximo:
            return etiqueta
    return "Riesgo alto"


def calcular_indice_salud_negocio(comparativo_incumplimientos: pd.DataFrame,
                                   historico_gmm: pd.DataFrame,
                                   historico_actividad: pd.DataFrame) -> pd.DataFrame:
    if comparativo_incumplimientos is None or comparativo_incumplimientos.empty:
        return pd.DataFrame()
    base = comparativo_incumplimientos[["ID_Asesor", "ID_Periodo", "IGC_Indice_Real", "LIMRA_Indice_Real"]].copy()

    if historico_gmm is not None and not historico_gmm.empty:
        prod_gmm = historico_gmm.groupby(["ID_Asesor", "ID_Periodo"]).agg(
            Prima_GMM=("Primas_Iniciales_Mes", "sum"), Polizas_GMM=("Polizas_Mes", "sum")).reset_index()
        base = base.merge(prod_gmm, on=["ID_Asesor", "ID_Periodo"], how="left")
    else:
        base["Prima_GMM"], base["Polizas_GMM"] = np.nan, np.nan

    if historico_actividad is not None and not historico_actividad.empty:
        act = historico_actividad.groupby(["ID_Asesor", "ID_Periodo"])["Polizas_Vida"].sum().reset_index()
        base = base.merge(act, on=["ID_Asesor", "ID_Periodo"], how="left")
    else:
        base["Polizas_Vida"] = np.nan
    # Prima Vida: no existe un reporte separado de "prima de vida pagada" en
    # el sistema -- se aproxima con la prima conservada de IGC, ya
    # documentado como aproximacion en el resto del sistema.
    if "Prima_PorConservar_Total" in comparativo_incumplimientos.columns:
        base["Prima_Vida"] = comparativo_incumplimientos["Prima_PorConservar_Total"]
    else:
        base["Prima_Vida"] = np.nan

    if base.dropna(subset=["IGC_Indice_Real", "LIMRA_Indice_Real"], how="all").empty:
        return pd.DataFrame()

    # --- Deteccion del caso "valor 100 = sin produccion" ---
    # Confirmado por el director segun Gerardo, pero marcado para validar
    # contra los datos reales de un mes con este caso presente. Si LIMRA o
    # IGC es exactamente 100 Y el asesor no tuvo produccion alguna ese
    # periodo (0 polizas de vida y 0 GMM), se excluye esa variable del
    # promedio ponderado en vez de contarla como "Extraordinario" -- una
    # cartera sin actividad no es lo mismo que una cartera excelente.
    sin_produccion = (base["Polizas_Vida"].fillna(0) == 0) & (base["Polizas_GMM"].fillna(0) == 0)
    base["LIMRA_Excluido_Sin_Produccion"] = sin_produccion & (base["LIMRA_Indice_Real"] == 100)
    base["IGC_Excluido_Sin_Produccion"] = sin_produccion & (base["IGC_Indice_Real"] == 100)

    filas = []
    for _, r in base.iterrows():
        niveles = {
            "Polizas_Vida": _nivel_polizas_vida(r["Polizas_Vida"]),
            "Prima_Vida": _nivel_prima_vida(r["Prima_Vida"]),
            "Polizas_GMM": _nivel_polizas_gmm(r["Polizas_GMM"]),
            "Prima_GMM": _nivel_prima_gmm(r["Prima_GMM"]),
            "LIMRA": None if r["LIMRA_Excluido_Sin_Produccion"] else _nivel_limra(r["LIMRA_Indice_Real"]),
            "IGC": None if r["IGC_Excluido_Sin_Produccion"] else _nivel_igc(r["IGC_Indice_Real"]),
        }
        peso_disponible = sum(PESOS_INDICE_SALUD[v] for v, n in niveles.items() if n is not None)
        if peso_disponible == 0:
            indice = None
        else:
            suma = sum(PESOS_INDICE_SALUD[v] * PUNTAJE_POR_NIVEL[n] for v, n in niveles.items() if n is not None)
            indice = round(suma / peso_disponible, 2)

        fila = {"ID_Asesor": r["ID_Asesor"], "ID_Periodo": r["ID_Periodo"],
                "Polizas_Vida": r["Polizas_Vida"], "Prima_Vida": r["Prima_Vida"],
                "Polizas_GMM": r["Polizas_GMM"], "Prima_GMM": r["Prima_GMM"],
                "LIMRA_Indice_Real": r["LIMRA_Indice_Real"], "IGC_Indice_Real": r["IGC_Indice_Real"],
                "Indice_Salud_Negocio": indice,
                "Segmento": _lectura_final(indice) if indice is not None else "Datos insuficientes",
                "LIMRA_Excluido_Sin_Produccion": r["LIMRA_Excluido_Sin_Produccion"],
                "IGC_Excluido_Sin_Produccion": r["IGC_Excluido_Sin_Produccion"]}
        for v, n in niveles.items():
            fila[f"Nivel_{v}"] = n or "No evaluable"
            # Puntaje/Puntos por variable -- nunca se usaban fuera de esta
            # funcion, se exponen aqui para que la interfaz pueda mostrar el
            # desglose completo (por que un asesor llego a su Indice de
            # Salud) sin recalcular nada. Puntos_{v} = peso% x puntaje/100 --
            # la suma de los 6 Puntos_* de un asesor sin variables faltantes
            # da exactamente su Indice_Salud_Negocio.
            fila[f"Puntaje_{v}"] = PUNTAJE_POR_NIVEL[n] if n is not None else None
            fila[f"Puntos_{v}"] = round(PESOS_INDICE_SALUD[v] * PUNTAJE_POR_NIVEL[n] / 100, 2) if n is not None else None
        filas.append(fila)

    resultado = pd.DataFrame(filas)

    # Reglas de control (del documento fuente): el promedio ponderado no
    # debe ocultar un problema grave -- cero produccion de Vida, o deterioro
    # relevante en LIMRA/IGC, limita la clasificacion final aunque el
    # promedio numerico sea mas alto.
    limite_por_control = resultado.apply(
        lambda r: "Riesgo alto" if (r["Polizas_Vida"] == 0 and not pd.isna(r["Polizas_Vida"])) else
                  ("Riesgo medio" if r["Nivel_LIMRA"] == "Riesgo Alto" or r["Nivel_IGC"] == "Riesgo Alto" else None),
        axis=1)
    orden_bandas = ["Riesgo alto", "Riesgo medio", "Negocio en desarrollo", "Negocio saludable",
                     "Alto desempeno", "Negocio extraordinario"]
    for i, row in resultado.iterrows():
        limite = limite_por_control.iloc[i]
        if limite is not None and pd.notna(limite) and row["Segmento"] in orden_bandas:
            if orden_bandas.index(limite) < orden_bandas.index(row["Segmento"]):
                resultado.at[i, "Segmento"] = limite
                resultado.at[i, "Regla_de_Control_Aplicada"] = "Si -- ver Polizas_Vida/LIMRA/IGC"
                continue
        resultado.at[i, "Regla_de_Control_Aplicada"] = "No"

    return resultado


# Se conserva el nombre de funcion anterior como alias, para no romper
# el resto del sistema que ya la importa con este nombre.
def calcular_segmentacion_asesores(comparativo_incumplimientos, historico_gmm, historico_actividad):
    return calcular_indice_salud_negocio(comparativo_incumplimientos, historico_gmm, historico_actividad)


# ---------------------------------------------------------------------------
# Deteccion de anomalias (traspasos y produccion GMM)
# ---------------------------------------------------------------------------

def detectar_anomalias(historico_traspasos: pd.DataFrame, historico_gmm: pd.DataFrame) -> pd.DataFrame:
    resultados = []
    if historico_traspasos is not None and len(historico_traspasos) >= 5:
        modelo = IsolationForest(contamination=0.1, random_state=42)
        et = modelo.fit_predict(historico_traspasos[["Prima_Pago"]].fillna(0))
        out = historico_traspasos.copy()
        out["Es_Anomalia"] = et == -1
        an = out[out["Es_Anomalia"]].copy()
        an["Fuente"], an["Motivo_Sugerido"] = "Traspasos", "Monto de traspaso atipico respecto al periodo"
        resultados.append(an[["Fuente", "ID_Asesor", "ID_Periodo", "Prima_Pago", "Motivo_Sugerido"]])
    if historico_gmm is not None and len(historico_gmm) >= 5:
        modelo = IsolationForest(contamination=0.1, random_state=42)
        et = modelo.fit_predict(historico_gmm[["Primas_Iniciales_Mes"]].fillna(0))
        out = historico_gmm.copy()
        out["Es_Anomalia"] = et == -1
        an = out[out["Es_Anomalia"]].copy()
        an["Fuente"], an["Motivo_Sugerido"] = "GMM", "Produccion atipica respecto al periodo"
        an = an.rename(columns={"Primas_Iniciales_Mes": "Prima_Pago"})
        resultados.append(an[["Fuente", "ID_Asesor", "ID_Periodo", "Prima_Pago", "Motivo_Sugerido"]])
    if not resultados:
        return pd.DataFrame(columns=["Fuente", "ID_Asesor", "ID_Periodo", "Prima_Pago", "Motivo_Sugerido"])
    return pd.concat(resultados, ignore_index=True)


def _meses_antiguedad_local(fecha_ingreso_str, fecha_referencia):
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


# ---------------------------------------------------------------------------
# Costeo de asesores (Objetivo 5)
# ---------------------------------------------------------------------------

def calcular_costeo_asesores(dim_asesor: pd.DataFrame, id_periodo: str, sueldo_sharon: float,
                              pct_sharon: float, gastos_canales: dict,
                              resumen_bonos: pd.DataFrame) -> pd.DataFrame:
    """Ya NO recibe costos_fijos como parametro manual -- se calcula
    automaticamente a partir del presupuesto real de 35 conceptos
    (PRESUPUESTO_YAKOL), prorrateado segun el numero de funciones de la
    promotoria (NUMERO_FUNCIONES_PROMOTORIA), tal como Gerardo indico."""
    fecha_ref = date(int(id_periodo[:4]), int(id_periodo[4:6]), 1)
    dim = dim_asesor.copy()
    dim["Meses_Antiguedad"] = dim["Fecha_Ingreso"].apply(lambda f: _meses_antiguedad_local(f, fecha_ref))
    n_nuevos = int((dim["Meses_Antiguedad"] == 0).sum())

    presupuesto_total_mes = calcular_presupuesto_mensualizado()
    presupuesto_atribuible_reclutamiento = round(presupuesto_total_mes / NUMERO_FUNCIONES_PROMOTORIA, 2)

    costo_sharon = sueldo_sharon * (pct_sharon / 100.0)
    costo_canales = sum(gastos_canales.values())
    costo_total = costo_sharon + costo_canales + presupuesto_atribuible_reclutamiento
    costo_por_asesor = round(costo_total / n_nuevos, 2) if n_nuevos else None

    filas = [
        {"Concepto": "Sueldo proporcional de Sharon", "Monto": round(costo_sharon, 2)},
        {"Concepto": "Gasto total en canales de reclutamiento", "Monto": round(costo_canales, 2)},
        {"Concepto": f"Presupuesto general atribuible a reclutamiento (1/{NUMERO_FUNCIONES_PROMOTORIA} del total, "
                      f"${presupuesto_total_mes:,.2f}/mes en {len(PRESUPUESTO_YAKOL)} conceptos reales; "
                      f"Nomina Carmen excluida por no ser atribuible a reclutamiento)",
         "Monto": presupuesto_atribuible_reclutamiento},
        {"Concepto": "COSTO TOTAL DEL MES", "Monto": round(costo_total, 2)},
        {"Concepto": "Asesores nuevos en el periodo", "Monto": n_nuevos},
        {"Concepto": "Costo promedio por asesor nuevo",
         "Monto": costo_por_asesor if costo_por_asesor is not None else "Sin asesores nuevos este mes"},
    ]
    if costo_por_asesor is not None and resumen_bonos is not None and not resumen_bonos.empty:
        sub = resumen_bonos[resumen_bonos["ID_Periodo"] == id_periodo]
        bono_total_mes = sub["Bono_Total"].iloc[0] if len(sub) else 0
        ingreso_por_asesor = bono_total_mes / max(len(dim), 1)
        payback = round(costo_por_asesor / ingreso_por_asesor, 1) if ingreso_por_asesor > 0 else None
        filas.append({"Concepto": "Punto de equilibrio (payback) de reclutamiento",
                      "Monto": f"{payback} meses (aproximado)" if payback else "No calculable este mes"})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# ROI de campanas (Objetivo 6) -- usa Bono_Total OFICIAL, nunca recalculado
# ---------------------------------------------------------------------------

def calcular_roi_campanas(resumen_bonos: pd.DataFrame, id_periodo: str, costo_campana_interna: float) -> pd.DataFrame:
    bono_smnyl = 0.0
    if resumen_bonos is not None and not resumen_bonos.empty:
        sub = resumen_bonos[resumen_bonos["ID_Periodo"] == id_periodo]
        if len(sub):
            bono_smnyl = sub["Bono_Total"].iloc[0] or 0.0

    filas = [{
        "Tipo_Campana": "Campanas de SMNYL (sin costo para el promotor)",
        "Costo": 0.0, "Bono_Oficial_Recibido": round(bono_smnyl, 2),
        "ROI": "Ganancia neta (sin costo)" if bono_smnyl > 0 else "Sin bono oficial este periodo",
    }]
    if costo_campana_interna > 0:
        roi_pct = round((bono_smnyl - costo_campana_interna) / costo_campana_interna * 100, 1)
        filas.append({
            "Tipo_Campana": "Campana interna de Yakol (costo capturado este mes)",
            "Costo": round(costo_campana_interna, 2), "Bono_Oficial_Recibido": round(bono_smnyl, 2),
            "ROI": f"{roi_pct}%",
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Real vs. Plan -- meta anual confirmada por el director (300/18)
# ---------------------------------------------------------------------------

def calcular_real_vs_plan(historico_actividad: pd.DataFrame, dim_asesor: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    mes_num = int(id_periodo[4:6])
    meta_polizas = round(META_ANUAL_POLIZAS_VIDA / 12 * mes_num, 1)
    meta_asesores = round(META_ANUAL_ASESORES_NUEVOS / 12 * mes_num, 1)

    polizas_reales = 0
    if historico_actividad is not None and not historico_actividad.empty:
        sub = historico_actividad[historico_actividad["ID_Periodo"] == id_periodo]
        if len(sub):
            polizas_reales = sub["Polizas_Vida"].sum()

    asesores_nuevos_acum = 0
    if dim_asesor is not None and not dim_asesor.empty:
        fecha_ref = date(int(id_periodo[:4]), int(id_periodo[4:6]), 1)
        dim = dim_asesor.copy()
        dim["Meses_Antiguedad"] = dim["Fecha_Ingreso"].apply(lambda f: _meses_antiguedad_local(f, fecha_ref))
        asesores_nuevos_acum = int((dim["Meses_Antiguedad"] <= mes_num - 1).sum())

    return pd.DataFrame([
        {"Indicador": "Polizas de vida (acumulado a la fecha)", "Meta_Prorrateada": meta_polizas,
         "Real": polizas_reales, "Avance_Pct": round(polizas_reales / meta_polizas * 100, 1) if meta_polizas else None},
        {"Indicador": "Asesores nuevos (acumulado a la fecha)", "Meta_Prorrateada": meta_asesores,
         "Real": asesores_nuevos_acum, "Avance_Pct": round(asesores_nuevos_acum / meta_asesores * 100, 1) if meta_asesores else None},
    ])


# ---------------------------------------------------------------------------
# Analisis de sensibilidad (tornado) -- sobre el Bono_Total OFICIAL
# ---------------------------------------------------------------------------

def calcular_analisis_sensibilidad(resumen_bonos: pd.DataFrame, id_periodo: str) -> pd.DataFrame:
    if resumen_bonos is None or resumen_bonos.empty:
        return pd.DataFrame()
    sub = resumen_bonos[resumen_bonos["ID_Periodo"] == id_periodo]
    if not len(sub):
        return pd.DataFrame()
    igc_base, limra_base = sub["IGC"].iloc[0] or 80.0, sub["LIMRA"].iloc[0] or 80.0
    bono_base = sub["Bono_Total"].iloc[0] or 0.0

    def bono_estimado(igc, limra):
        factor = ((igc / 100) + (limra / 100)) / 2
        return max(bono_base * (1 + (factor - 0.86)), 0)

    filas = []
    for delta in (-0.20, -0.10, 0.10, 0.20):
        filas.append({"Variable": "IGC", "Cambio_Pct": delta * 100,
                      "Bono_Resultante_Estimado": round(bono_estimado(igc_base * (1 + delta), limra_base), 2)})
        filas.append({"Variable": "LIMRA", "Cambio_Pct": delta * 100,
                      "Bono_Resultante_Estimado": round(bono_estimado(igc_base, limra_base * (1 + delta)), 2)})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Escenarios Monte Carlo (recalibrado con variacion real observada)
# ---------------------------------------------------------------------------

N_SIMULACIONES = 10000


def _cv_empirico(serie, default):
    serie = [v for v in serie if v is not None and not pd.isna(v)]
    if len(serie) < 3:
        return default
    s = np.array(serie, dtype=float)
    var_pct = np.diff(s) / np.where(s[:-1] == 0, np.nan, s[:-1])
    var_pct = var_pct[~np.isnan(var_pct)]
    return max(float(np.std(var_pct, ddof=1)), 0.01) if len(var_pct) >= 2 else default


def calcular_escenarios_montecarlo(resumen_bonos: pd.DataFrame) -> pd.DataFrame:
    if resumen_bonos is None or len(resumen_bonos) < 2:
        return pd.DataFrame()
    df = resumen_bonos.sort_values("ID_Periodo")
    igc_base, limra_base = df["IGC"].iloc[-1], df["LIMRA"].iloc[-1]

    # Usar el promedio de los ultimos periodos con bono positivo como base,
    # en vez de solo el ultimo mes -- si el ultimo mes fue $0 (como paso con
    # el Bono de Desarrollo desde marzo), tomar solo ese valor colapsaria
    # toda la simulacion a cero, lo cual no representa un escenario util.
    bonos_recientes = df["Bono_Total"].tail(5)
    bonos_positivos = bonos_recientes[bonos_recientes > 0]
    bono_base = bonos_positivos.mean() if len(bonos_positivos) else 0.0
    nota_base = (
        f"Base calculada como el promedio de los ultimos {len(bonos_positivos)} periodo(s) con bono "
        f"positivo (el ultimo mes disponible tuvo ${df['Bono_Total'].iloc[-1]:,.0f})."
        if len(bonos_positivos) else "Sin ningun periodo con bono positivo en el historico disponible -- "
        "no es posible generar un escenario util todavia."
    )

    cv_igc = _cv_empirico(df["IGC"].tolist(), default=0.08)
    cv_limra = _cv_empirico(df["LIMRA"].tolist(), default=0.08)

    rng = np.random.default_rng(42)
    filas = []
    for incremento in (0.05, 0.10):
        s_igc = np.clip(rng.normal(igc_base * (1 + incremento), max(igc_base, 1) * cv_igc, N_SIMULACIONES), 0, 100)
        s_limra = np.clip(rng.normal(limra_base * (1 + incremento), max(limra_base, 1) * cv_limra, N_SIMULACIONES), 0, 100)
        factor = ((s_igc / 100) + (s_limra / 100)) / 2
        s_bono = np.clip(bono_base * (1 + (factor - 0.86)), 0, None)
        filas.append({
            "Escenario": f"Incremento de persistencia +{incremento*100:.0f}%",
            "Bono_P10_Pesimista": round(np.percentile(s_bono, 10), 2),
            "Bono_P50_Esperado": round(np.percentile(s_bono, 50), 2),
            "Bono_P90_Optimista": round(np.percentile(s_bono, 90), 2),
            "CV_IGC_Empirico": round(cv_igc, 4), "CV_LIMRA_Empirico": round(cv_limra, 4),
            "Nota_Base_Calculo": nota_base,
        })
    return pd.DataFrame(filas)


def calcular_tendencia_proyeccion(resumen_bonos: pd.DataFrame) -> pd.DataFrame:
    """Regresion lineal simple sobre IGC/LIMRA/Bono_Total del promotor --
    proyeccion preliminar, no un modelo estacional (requeriria 24+ meses)."""
    if resumen_bonos is None or len(resumen_bonos) < 3:
        return pd.DataFrame()
    df = resumen_bonos.sort_values("ID_Periodo").reset_index(drop=True)
    x = np.arange(len(df))
    filas = []
    for var in ["IGC", "LIMRA", "Bono_Total"]:
        y = df[var].astype(float).values
        mask = ~np.isnan(y)
        if mask.sum() < 3:
            continue
        pendiente, intercepto = np.polyfit(x[mask], y[mask], 1)
        proyeccion = pendiente * (x.max() + 1) + intercepto
        filas.append({"Variable": var, "Pendiente_Mensual": round(pendiente, 3),
                      "Proyeccion_Siguiente_Periodo": round(proyeccion, 2)})
    return pd.DataFrame(filas)
