"""
reglas_cuaderno.py -- Motor de reglas del Cuaderno de Concursos 2004-2026
------------------------------------------------------------------------------
IMPORTANTE -- este modulo NUNCA sustituye el bono oficial de Resumen_Bonos.
Su unico proposito es EXPLICAR, usando las formulas del Cuaderno, por que un
bono se obtuvo o no se obtuvo, y proyectar un mes futuro. El resultado de
este modulo se escribe en hojas separadas ("Explicacion_Bonos" y
"Proyeccion_Bonos_Siguiente_Mes"), siempre etiquetadas como analisis
explicativo/estimado -- nunca como el dato oficial.

Alcance realista: solo se recalculan los bonos para los cuales el sistema
tiene informacion suficiente y confiable. Los que requieren datos que no
existen en ningun reporte procesado (Bono de Crecimiento, Bono Anual de
Crecimiento GMMI, Bono Anual por Siniestralidad -- los tres necesitan datos
del anio anterior o de siniestros que SMNYL no incluye) se marcan
explicitamente como "no calculable", nunca se estiman con supuestos.

Yakol opera bajo el esquema "Promotor Nuevo Consolidado" (49+ meses de
antiguedad); el esquema "Training" (1-48 meses) no se implementa.
"""

from datetime import date

import numpy as np
import pandas as pd

IGC_MINIMO_CONSOLIDADO = 90.25
LIMRA_MINIMO_CONSOLIDADO = 86.0

# Tabla 11 -- Prima Meta Nueva Organizacion (miles $) por grupo (1-17) y mes
TABLA_11_PRIMA_META_NO = {
    1: [1490, 2980, 4470, 5965, 7455, 8945, 1715, 3445, 5165, 6875, 8600, 10315],
    2: [1370, 2755, 4125, 5505, 6875, 8255, 1535, 3050, 4580, 6110, 7635, 9160],
    3: [1260, 2520, 3780, 5045, 6305, 7570, 1415, 2830, 4235, 5650, 7065, 8480],
    4: [1140, 2290, 3435, 4580, 5720, 6870, 1300, 2585, 3885, 5190, 6490, 7785],
    5: [1030, 2055, 3095, 4120, 5150, 6175, 1195, 2375, 3550, 4740, 5925, 7110],
    6: [980, 1960, 2945, 3920, 4900, 5885, 1180, 2360, 3535, 4710, 5890, 7060],
    7: [900, 1815, 2710, 3605, 4520, 5420, 1025, 2045, 3070, 4090, 5115, 6130],
    8: [830, 1645, 2470, 3305, 4120, 4950, 900, 1815, 2710, 3605, 4520, 5415],
    9: [795, 1575, 2370, 3140, 3935, 4720, 860, 1725, 2585, 3455, 4325, 5180],
    10: [705, 1410, 2115, 2835, 3530, 4235, 830, 1645, 2470, 3305, 4120, 4950],
    11: [670, 1335, 2010, 2670, 3345, 4005, 795, 1575, 2370, 3140, 3935, 4725],
    12: [635, 1270, 1905, 2550, 3175, 3810, 750, 1500, 2255, 3015, 3770, 4520],
    13: [595, 1195, 1780, 2380, 2975, 3575, 670, 1355, 2025, 2695, 3375, 4045],
    14: [555, 1105, 1660, 2220, 2770, 3320, 635, 1270, 1905, 2550, 3175, 3810],
    15: [520, 1030, 1550, 2060, 2580, 3100, 555, 1105, 1660, 2220, 2770, 3320],
    16: [475, 950, 1435, 1905, 2385, 2855, 520, 1030, 1550, 2060, 2580, 3100],
    17: [400, 795, 1195, 1585, 1975, 2380, 475, 950, 1435, 1905, 2385, 2855],
}
TABLA_12_PCT_BONO_INICIAL = {
    1: (20.0, 5.0), 2: (18.0, 4.7), 3: (16.0, 4.4), 4: (14.0, 4.1), 5: (13.0, 3.8),
    6: (12.0, 3.5), 7: (11.0, 3.2), 8: (10.0, 2.9), 9: (9.0, 2.6), 10: (8.0, 2.3),
    11: (7.0, 2.0), 12: (6.5, 1.7), 13: (6.0, 1.4), 14: (5.5, 1.1), 15: (5.0, 1.0),
    16: (4.5, 0.9), 17: (4.0, 0.8),
}
# Tablas 14/15 -- solo grupos 1-14 generan Bono Renovacion (correccion
# confirmada: los grupos 15-17 obtienen Bono Inicial pero NUNCA Renovacion)
TABLA_14_RENOVACION_NVA_ORG = {
    1: {90.25: 2.0, 94.00: 3.0, 95.00: 4.0}, 2: {90.25: 1.9, 94.00: 2.9, 95.00: 3.8},
    3: {90.25: 1.8, 94.00: 2.7, 95.00: 3.6}, 4: {90.25: 1.7, 94.00: 2.6, 95.00: 3.4},
    5: {90.25: 1.6, 94.00: 2.4, 95.00: 3.2}, 6: {90.25: 1.5, 94.00: 2.3, 95.00: 3.0},
    7: {90.25: 1.4, 94.00: 2.1, 95.00: 2.8}, 8: {90.25: 1.3, 94.00: 2.0, 95.00: 2.6},
    9: {90.25: 1.2, 94.00: 1.8, 95.00: 2.4}, 10: {90.25: 1.1, 94.00: 1.7, 95.00: 2.2},
    11: {90.25: 1.0, 94.00: 1.5, 95.00: 2.0}, 12: {90.25: 0.9, 94.00: 1.4, 95.00: 1.8},
    13: {90.25: 0.8, 94.00: 1.2, 95.00: 1.6}, 14: {90.25: 0.7, 94.00: 1.1, 95.00: 1.4},
}
TABLA_15_RENOVACION_CONSOLIDADOS = {
    1: {90.25: 1.00, 94.00: 1.50, 95.00: 2.00}, 2: {90.25: 0.95, 94.00: 1.43, 95.00: 1.90},
    3: {90.25: 0.90, 94.00: 1.35, 95.00: 1.80}, 4: {90.25: 0.85, 94.00: 1.28, 95.00: 1.70},
    5: {90.25: 0.80, 94.00: 1.20, 95.00: 1.60}, 6: {90.25: 0.75, 94.00: 1.13, 95.00: 1.50},
    7: {90.25: 0.70, 94.00: 1.05, 95.00: 1.40}, 8: {90.25: 0.65, 94.00: 0.97, 95.00: 1.30},
    9: {90.25: 0.60, 94.00: 0.90, 95.00: 1.20}, 10: {90.25: 0.55, 94.00: 0.82, 95.00: 1.10},
    11: {90.25: 0.50, 94.00: 0.75, 95.00: 1.00}, 12: {90.25: 0.45, 94.00: 0.67, 95.00: 0.90},
    13: {90.25: 0.40, 94.00: 0.60, 95.00: 0.80}, 14: {90.25: 0.35, 94.00: 0.52, 95.00: 0.70},
}
TABLA_16_GMMI_INICIALES = {
    1: (7045, 50, 3.6), 2: (5870, 45, 3.3), 3: (5145, 35, 3.2),
    4: (3735, 30, 2.9), 5: (2345, 25, 2.3), 6: (1695, 20, 1.6),
}
TABLA_19_GMMI_RENOVACION = {
    1: (42065, 65, 1.15), 2: (32575, 55, 1.00), 3: (21905, 45, 0.75),
    4: (14205, 35, 0.50), 5: (8770, 25, 0.30),
}
TABLA_21_BONO_CONEXION = {3: 5000, 4: 9000, 5: 15000, 6: 20000}
TABLA_22_BONO_DESARROLLO = {2: 5000, 3: 9000, 4: 15000}
TABLA_23_SUBSIDIO_RENTA = [
    (990, 0.0), (1110, 6.0), (1400, 9.0), (1690, 11.0), (2155, 14.0),
    (2740, 17.0), (3380, 21.0), (4025, 23.0), (float("inf"), 25.0),
]

# Bonos que NUNCA se estiman por falta de datos -- se documentan asi, no se
# inventan con supuestos.
BONOS_NO_CALCULABLES = {
    "Bono de Crecimiento": "Requiere Prima Meta del mismo semestre del anio anterior (2025), "
                             "dato que no forma parte de ningun reporte procesado por el sistema.",
    "Bono Anual de Crecimiento GMMI": "Misma razon: requiere primas iniciales GMM del anio anterior.",
    "Bono Anual por Siniestralidad": "Requiere el monto de siniestros pagados, dato que SMNYL no "
                                       "incluye en ninguno de los 10 reportes que el sistema procesa.",
}


class Condicion:
    def __init__(self, regla, requerido, real, cumple):
        self.regla, self.requerido, self.real, self.cumple = regla, requerido, real, cumple

    def a_texto(self):
        simbolo = "CUMPLE" if self.cumple else "NO CUMPLE"
        return f"[{simbolo}] {self.regla}: requerido {self.requerido}, real {self.real}"


def _grupo_por_tabla11(prima_meta_no_acumulada, mes_num):
    idx = mes_num - 1
    for grupo in range(1, 18):
        if prima_meta_no_acumulada >= TABLA_11_PRIMA_META_NO[grupo][idx] * 1000:
            return grupo
    return None


def _nivel_igc(igc_real):
    if igc_real >= 95.00:
        return 95.00
    if igc_real >= 94.00:
        return 94.00
    if igc_real >= IGC_MINIMO_CONSOLIDADO:
        return 90.25
    return None


def evaluar_bono_inicial(prima_meta_no_acum, prima_meta_cons_acum, limra_real, mes_num,
                          ganadores_training_allowance=None,
                          nivel_confianza_prima="aproximado (sin ponderacion exacta por producto, Tabla 1)"):
    cumple_training = None if ganadores_training_allowance is None else ganadores_training_allowance >= 3
    condiciones = [
        Condicion("LIMRA minimo (Consolidados)", f"{LIMRA_MINIMO_CONSOLIDADO}%", f"{limra_real:.2f}%",
                   limra_real >= LIMRA_MINIMO_CONSOLIDADO),
        Condicion("3 asesores ganadores de Training Allowance (ultimos 6 meses)",
                   "3",
                   "No capturado" if ganadores_training_allowance is None else str(ganadores_training_allowance),
                   cumple_training),
    ]
    grupo = _grupo_por_tabla11(prima_meta_no_acum, mes_num)
    condiciones.append(Condicion(
        "Prima Meta Nueva Organizacion acumulada vs. umbral de grupo (Tabla 11)",
        f"grupo alcanzado: {grupo if grupo else 'ninguno (por debajo del Grupo 17)'}",
        f"${prima_meta_no_acum:,.2f} ({nivel_confianza_prima})",
        grupo is not None,
    ))

    # Solo se otorga el bono si TODAS las condiciones evaluables se cumplen
    # -- si Training Allowance no fue capturado, el bono se marca como
    # "pendiente de confirmar" en vez de otorgarse por omision.
    condiciones_evaluables = [c for c in condiciones if c.cumple is not None]
    cumple_verificable = all(c.cumple for c in condiciones_evaluables)
    puede_calcularse_monto = cumple_verificable and cumple_training is True

    monto = 0.0
    if puede_calcularse_monto and grupo is not None and limra_real >= LIMRA_MINIMO_CONSOLIDADO:
        pct_no, pct_cons = TABLA_12_PCT_BONO_INICIAL[grupo]
        monto = round(prima_meta_no_acum * (pct_no / 100) + prima_meta_cons_acum * (pct_cons / 100), 2)

    nivel_confianza = "Alto -- todas las condiciones evaluadas con datos capturados" \
        if ganadores_training_allowance is not None else \
        "Aproximado -- falta capturar el numero de ganadores de Training Allowance"

    return {
        "Bono": "Bono Inicial (Vida)", "Grupo_Alcanzado": grupo,
        "Monto_Estimado": monto, "Condiciones_Verificables_Cumplen": cumple_verificable,
        "Nivel_Confianza": nivel_confianza,
        "Condiciones": condiciones,
    }


def evaluar_bono_renovacion(bono_inicial_monto, grupo_inicial, igc_real,
                              prima_ren_no_acum, prima_ren_cons_acum):
    condiciones = [
        Condicion("Bono Inicial calculado en el mes", "> $0", f"${bono_inicial_monto:,.2f}", bono_inicial_monto > 0),
        Condicion("Grupo en rango 1-14 (los grupos 15-17 no generan Renovacion)",
                   "1 a 14", str(grupo_inicial), grupo_inicial is not None and 1 <= grupo_inicial <= 14),
        Condicion("IGC minimo (Consolidados)", f"{IGC_MINIMO_CONSOLIDADO}%", f"{igc_real:.2f}%",
                   igc_real >= IGC_MINIMO_CONSOLIDADO),
    ]
    cumple_todas = all(c.cumple for c in condiciones)
    monto = 0.0
    if cumple_todas:
        nivel = _nivel_igc(igc_real)
        pct_no = TABLA_14_RENOVACION_NVA_ORG[grupo_inicial][nivel]
        pct_cons = TABLA_15_RENOVACION_CONSOLIDADOS[grupo_inicial][nivel]
        monto = round(prima_ren_no_acum * (pct_no / 100) + prima_ren_cons_acum * (pct_cons / 100), 2)
    return {
        "Bono": "Bono Renovacion (Vida)", "Monto_Estimado": monto,
        "Condiciones_Verificables_Cumplen": cumple_todas,
        "Nivel_Confianza": "Aproximado -- depende del Bono Inicial estimado arriba",
        "Condiciones": condiciones,
    }


def evaluar_bono_conexion(polizas_mes2_3):
    umbral = max([u for u in TABLA_21_BONO_CONEXION if polizas_mes2_3 >= u], default=None)
    monto = TABLA_21_BONO_CONEXION.get(umbral, 0.0)
    condiciones = [Condicion("Polizas del Asesor Conectado (mes 2 o 3)", "3 o mas", str(polizas_mes2_3),
                               umbral is not None)]
    return {"Bono": "Bono de Conexion", "Monto_Estimado": monto,
            "Condiciones_Verificables_Cumplen": umbral is not None,
            "Nivel_Confianza": "Alto -- formula directa de Tabla 21 sobre datos completos",
            "Condiciones": condiciones}


def evaluar_bono_desarrollo(polizas_mes):
    umbral = max([u for u in TABLA_22_BONO_DESARROLLO if polizas_mes >= u], default=None)
    monto = TABLA_22_BONO_DESARROLLO.get(umbral, 0.0)
    condiciones = [Condicion("Polizas del Asesor en Desarrollo (mes 4-15)", "2 o mas", str(polizas_mes),
                               umbral is not None)]
    return {"Bono": "Bono de Desarrollo", "Monto_Estimado": monto,
            "Condiciones_Verificables_Cumplen": umbral is not None,
            "Nivel_Confianza": "Alto -- formula directa de Tabla 22 sobre datos completos",
            "Condiciones": condiciones}


def generar_explicacion_texto(resultado):
    partes = [c.a_texto() for c in resultado["Condiciones"]]
    return f"{resultado['Bono']}: " + "; ".join(partes)


# ---------------------------------------------------------------------------
# Explicacion de bonos del periodo (usa Resumen_Bonos oficial + Historico_*)
# ---------------------------------------------------------------------------

def generar_explicacion_bonos(resumen_bonos, hist_gmm, dim_asesor, ganadores_training_allowance=None):
    """Genera la explicacion para TODOS los periodos ya acumulados en
    Resumen_Bonos. Ya NO utiliza el reporte 'Detalle Bono de Conexion y
    Desarrollo' -- por decision de diseno, ese PDF se identifica durante
    el procesamiento (para confirmar que existe en el ZIP) pero su
    contenido nunca se incorpora al Excel Maestro. En consecuencia, esta
    hoja ya no puede evaluar ni explicar el Bono de Conexion ni el Bono de
    Desarrollo -- unicamente los bonos de Vida (Inicial/Renovacion)."""
    if resumen_bonos is None or resumen_bonos.empty:
        return pd.DataFrame()

    filas_salida = []
    for periodo in sorted(resumen_bonos["ID_Periodo"].astype(str).unique()):
        sub = resumen_bonos[resumen_bonos["ID_Periodo"].astype(str) == periodo]
        if not len(sub):
            continue
        fila = sub.iloc[0]
        igc_real, limra_real = fila["IGC"], fila["LIMRA"]
        mes_num = int(periodo[4:6])

        prima_proxy = 0.0
        if hist_gmm is not None and not hist_gmm.empty:
            sub_gmm = hist_gmm[hist_gmm["ID_Periodo"].astype(str) == periodo]
            prima_proxy = sub_gmm["Primas_Iniciales_Mes"].sum()

        r_inicial = evaluar_bono_inicial(prima_proxy, prima_proxy, limra_real, mes_num,
                                          ganadores_training_allowance=ganadores_training_allowance)
        r_renovacion = evaluar_bono_renovacion(r_inicial["Monto_Estimado"], r_inicial["Grupo_Alcanzado"],
                                                 igc_real, prima_proxy, prima_proxy)

        for resultado in (r_inicial, r_renovacion):
            filas_salida.append({
                "ID_Periodo": periodo, "Bono": resultado["Bono"],
                "Monto_Oficial_PDF": fila["Bono_Vida"],
                "Monto_Estimado_Segun_Cuaderno": resultado["Monto_Estimado"],
                "Nivel_Confianza": resultado["Nivel_Confianza"],
                "Explicacion": generar_explicacion_texto(resultado),
            })

        for nombre_bono, motivo in BONOS_NO_CALCULABLES.items():
            filas_salida.append({
                "ID_Periodo": periodo, "Bono": nombre_bono,
                "Monto_Oficial_PDF": fila.get(nombre_bono.replace(" ", "_"), None),
                "Monto_Estimado_Segun_Cuaderno": None,
                "Nivel_Confianza": "No calculable",
                "Explicacion": motivo,
            })

        # Bono de Conexion y Bono de Desarrollo: ya no evaluables, por la
        # decision de excluir el reporte de origen de esos datos.
        for nombre_bono in ("Bono Conexion (detalle por asesor)", "Bono Desarrollo (detalle por asesor)"):
            filas_salida.append({
                "ID_Periodo": periodo, "Bono": nombre_bono,
                "Monto_Oficial_PDF": fila.get(nombre_bono.split(" ")[1], None),
                "Monto_Estimado_Segun_Cuaderno": None,
                "Nivel_Confianza": "No calculable",
                "Explicacion": "El reporte 'Detalle Bono de Conexion y Desarrollo' ya no se incorpora "
                               "al Excel Maestro (decision de diseno para evitar registros transaccionales "
                               "de bajo valor analitico). El monto oficial del promotor sigue disponible "
                               "en Resumen_Bonos, pero ya no es posible explicar el detalle por asesor.",
            })

    return pd.DataFrame(filas_salida)


# ---------------------------------------------------------------------------
# Proyeccion de bonos a un mes futuro: proyecta IGC/LIMRA/prima con tendencia
# lineal simple (mismo metodo ya usado en Tendencia_Proyeccion) y corre esos
# valores proyectados por el mismo motor de reglas.
# ---------------------------------------------------------------------------

def _diagnostico_pendientes(condiciones):
    cumplidos = [c.regla for c in condiciones if c.cumple is True]
    pendientes = [c for c in condiciones if c.cumple is False]
    no_evaluables = [c for c in condiciones if c.cumple is None]
    return cumplidos, pendientes, no_evaluables


def _recomendacion_para_bono(nombre_bono, condiciones):
    _, pendientes, no_evaluables = _diagnostico_pendientes(condiciones)
    if not pendientes and not no_evaluables:
        return f"{nombre_bono}: cumple todos los requisitos evaluables."
    partes = []
    for c in pendientes:
        partes.append(f"falta cumplir '{c.regla}' (requerido {c.requerido}, proyectado {c.real})")
    for c in no_evaluables:
        partes.append(f"falta capturar el dato de '{c.regla}' para poder evaluarlo")
    return f"{nombre_bono}: " + "; ".join(partes) + "."


def generar_estimacion_bono_siguiente_periodo(resumen_bonos, hist_gmm, dim_promotor,
                                                ganadores_training_allowance=None):
    """Hoja tipo resumen ejecutivo: UN registro por promotor, con el
    analisis completo del periodo siguiente al ultimo procesado. Ya no
    depende del reporte de Conexion/Desarrollo (excluido del sistema), por
    lo que esos dos bonos se marcan explicitamente como no calculables.
    """
    if resumen_bonos is None or len(resumen_bonos) < 3:
        return pd.DataFrame([{
            "Nota": "Se requieren al menos 3 meses de historico para proyectar el periodo siguiente. "
                     "Esta hoja se completara automaticamente conforme se acumulen mas periodos."
        }])

    df = resumen_bonos.sort_values("ID_Periodo").reset_index(drop=True)
    x = np.arange(len(df))

    def _proyectar(serie):
        y = serie.astype(float).values
        mask = ~np.isnan(y)
        if mask.sum() < 3:
            return None
        pendiente, intercepto = np.polyfit(x[mask], y[mask], 1)
        return pendiente * (x.max() + 1) + intercepto

    igc_proy, limra_proy = _proyectar(df["IGC"]), _proyectar(df["LIMRA"])
    prima_proy = None
    if hist_gmm is not None and not hist_gmm.empty:
        prima_por_periodo = hist_gmm.groupby("ID_Periodo")["Primas_Iniciales_Mes"].sum().sort_index()
        if len(prima_por_periodo) >= 3:
            xp = np.arange(len(prima_por_periodo))
            pendiente, intercepto = np.polyfit(xp, prima_por_periodo.values, 1)
            prima_proy = max(pendiente * (xp.max() + 1) + intercepto, 0)

    if igc_proy is None or limra_proy is None or prima_proy is None:
        return pd.DataFrame([{"Nota": "Informacion insuficiente para proyectar todas las variables necesarias."}])

    ultimo_periodo = int(df["ID_Periodo"].iloc[-1])
    anio, mes = ultimo_periodo // 100, ultimo_periodo % 100
    mes_siguiente = mes + 1 if mes < 12 else 1
    anio_siguiente = anio if mes < 12 else anio + 1
    id_periodo_proyectado = f"{anio_siguiente}{mes_siguiente:02d}"

    id_promotor = dim_promotor["ID_Promotor"].iloc[0] if dim_promotor is not None and len(dim_promotor) else "PRM-0000"

    r_inicial = evaluar_bono_inicial(prima_proy, prima_proy, limra_proy, mes_siguiente,
                                      ganadores_training_allowance=ganadores_training_allowance,
                                      nivel_confianza_prima="proyectado por tendencia lineal, no observado")
    r_renovacion = evaluar_bono_renovacion(r_inicial["Monto_Estimado"], r_inicial["Grupo_Alcanzado"],
                                             igc_proy, prima_proy, prima_proy)

    fila = {
        "ID_Promotor": id_promotor,
        "ID_Periodo_Proyectado": id_periodo_proyectado,
        "IGC_Proyectado": round(igc_proy, 2),
        "LIMRA_Proyectado": round(limra_proy, 2),
        "Prima_Inicial_GMM_Proyectada": round(prima_proy, 2),

        "Bono_Inicial_Estado": "Cumple" if r_inicial["Condiciones_Verificables_Cumplen"] and r_inicial["Monto_Estimado"] > 0
                                else ("Pendiente de capturar Training Allowance" if ganadores_training_allowance is None
                                      else "No cumple"),
        "Bono_Inicial_Grupo_Estimado": r_inicial["Grupo_Alcanzado"],
        "Bono_Inicial_Monto_Estimado": r_inicial["Monto_Estimado"],
        "Bono_Inicial_Diagnostico": generar_explicacion_texto(r_inicial),

        "Bono_Renovacion_Estado": "Cumple" if r_renovacion["Condiciones_Verificables_Cumplen"] else "No cumple",
        "Bono_Renovacion_Monto_Estimado": r_renovacion["Monto_Estimado"],
        "Bono_Renovacion_Diagnostico": generar_explicacion_texto(r_renovacion),

        "Bono_Conexion_Estado": "No calculable",
        "Bono_Conexion_Diagnostico": "Requiere el reporte 'Detalle Bono de Conexion y Desarrollo', "
                                       "excluido del sistema por decision de diseno.",
        "Bono_Desarrollo_Estado": "No calculable",
        "Bono_Desarrollo_Diagnostico": "Misma razon que Bono de Conexion.",
        "Bono_Crecimiento_Estado": "No calculable",
        "Bono_Crecimiento_Diagnostico": BONOS_NO_CALCULABLES["Bono de Crecimiento"],
        "Bono_GMMI_Crecimiento_Estado": "No calculable",
        "Bono_GMMI_Crecimiento_Diagnostico": BONOS_NO_CALCULABLES["Bono Anual de Crecimiento GMMI"],
        "Bono_Siniestralidad_Estado": "No calculable",
        "Bono_Siniestralidad_Diagnostico": BONOS_NO_CALCULABLES["Bono Anual por Siniestralidad"],

        "Recomendacion_Bono_Inicial": _recomendacion_para_bono("Bono Inicial", r_inicial["Condiciones"]),
        "Recomendacion_Bono_Renovacion": _recomendacion_para_bono("Bono Renovacion", r_renovacion["Condiciones"]),
        "Nota_Metodologica": "IGC, LIMRA y Prima Inicial GMM se proyectan mediante regresion lineal simple "
                              "sobre el historico disponible (no es un modelo estacional). La Prima Meta de "
                              "Nueva Organizacion se aproxima con la prima inicial de GMM, ya que el sistema "
                              "no captura la ponderacion exacta por producto de la Tabla 1 del Cuaderno.",
    }
    return pd.DataFrame([fila])
