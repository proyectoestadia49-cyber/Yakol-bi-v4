"""
graficas.py -- Construccion de visualizaciones interactivas
-----------------------------------------------------------------
Cada funcion recibe un DataFrame YA CALCULADO por los modulos analiticos
(nunca recalcula nada financiero aqui) y regresa una figura de Plotly
lista para mostrarse con st.plotly_chart(). Colores e identidad visual
centralizados en config_visual.py.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from config_visual import (
    COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_ACENTO, COLOR_EXITO,
    COLOR_ADVERTENCIA, COLOR_PELIGRO, COLOR_NEUTRO, PALETA_SEGMENTOS, NIVEL_COLOR,
    FUENTE, PLANTILLA_PLOTLY,
)
from config import UMBRAL_LIMRA, UMBRAL_IGC

_ETIQUETAS_VARIABLE = {
    "Polizas_Vida": "Polizas Vida", "Prima_Vida": "Prima Vida",
    "Polizas_GMM": "Polizas GMM", "Prima_GMM": "Prima GMM",
    "LIMRA": "LIMRA", "IGC": "IGC",
}


def _figura_vacia(mensaje):
    fig = go.Figure()
    fig.add_annotation(text=mensaje, showarrow=False, font=dict(size=14, color=COLOR_NEUTRO))
    fig.update_layout(template=PLANTILLA_PLOTLY, height=280,
                       xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def grafica_tendencia_igc_limra(resumen_bonos: pd.DataFrame):
    if resumen_bonos is None or resumen_bonos.empty:
        return _figura_vacia("Sin historico suficiente todavia.")
    df = resumen_bonos.sort_values("ID_Periodo")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["ID_Periodo"], y=df["LIMRA"], mode="lines+markers",
                               name="LIMRA", line=dict(color=COLOR_ACENTO, width=3)))
    fig.add_trace(go.Scatter(x=df["ID_Periodo"], y=df["IGC"], mode="lines+markers",
                               name="IGC", line=dict(color=COLOR_PRIMARIO, width=3)))
    fig.add_hline(y=86.00, line_dash="dot", line_color=COLOR_ADVERTENCIA, opacity=0.6,
                   annotation_text="Minimo LIMRA 86.00%", annotation_position="bottom right",
                   annotation_font_size=10)
    fig.add_hline(y=90.25, line_dash="dot", line_color=COLOR_PELIGRO, opacity=0.6,
                   annotation_text="Minimo IGC 90.25%", annotation_position="top right",
                   annotation_font_size=10)
    fig.update_layout(
        title={"text": "EVOLUCION MENSUAL DE LIMRA E IGC DEL PROMOTOR RESPECTO A SUS MINIMOS OFICIALES",
               "font": {"size": 12.5, "color": COLOR_PRIMARIO}, "x": 0, "xanchor": "left", "y": 0.97},
        template=PLANTILLA_PLOTLY, height=380, font_family=FUENTE,
        margin=dict(l=10, r=10, t=95, b=10),
        legend=dict(orientation="h", yanchor="top", y=0.90, x=0, xanchor="left"))
    return fig


def interpretacion_tendencia_igc_limra(resumen_bonos: pd.DataFrame) -> str:
    if resumen_bonos is None or resumen_bonos.empty:
        return "Sin historico suficiente para interpretar la tendencia todavia."
    df = resumen_bonos.sort_values("ID_Periodo")
    ultimo = df.iloc[-1]
    limra_val, igc_val = ultimo["LIMRA"], ultimo["IGC"]
    partes = []
    if limra_val < 86.00:
        partes.append(f"LIMRA se ubica en {limra_val:.2f}%, por debajo del minimo oficial de 86.00%, "
                       f"lo cual representa un incumplimiento normativo que puede afectar el Bono Inicial del promotor.")
    else:
        margen_limra = limra_val - 86.00
        if margen_limra < 2:
            partes.append(f"LIMRA se ubica en {limra_val:.2f}%, apenas {margen_limra:.2f} puntos por encima "
                           f"del minimo de 86.00%, sin margen de holgura ante una variacion adversa.")
        else:
            partes.append(f"LIMRA se ubica en {limra_val:.2f}%, {margen_limra:.2f} puntos por encima del "
                           f"minimo de 86.00%, en cumplimiento con margen razonable.")
    if igc_val < 90.25:
        partes.append(f"IGC se ubica en {igc_val:.2f}%, por debajo del minimo oficial de 90.25%, "
                       f"lo cual representa un incumplimiento normativo que puede afectar el Bono de Renovacion.")
    else:
        margen_igc = igc_val - 90.25
        partes.append(f"IGC se ubica en {igc_val:.2f}%, {margen_igc:.2f} puntos por encima del minimo de 90.25%, "
                       f"en cumplimiento normativo.")
    if len(df) >= 2:
        anterior = df.iloc[-2]
        var_limra = limra_val - anterior["LIMRA"]
        tendencia = "en aumento" if var_limra > 0.5 else ("en descenso" if var_limra < -0.5 else "estable")
        partes.append(f"Respecto al periodo anterior, LIMRA se mantiene {tendencia} "
                       f"({var_limra:+.2f} puntos).")
    return " ".join(partes)


def grafica_bono_total_mensual(resumen_bonos: pd.DataFrame):
    if resumen_bonos is None or resumen_bonos.empty:
        return _figura_vacia("Sin historico suficiente todavia.")
    df = resumen_bonos.sort_values("ID_Periodo").copy()
    colores = [COLOR_NEUTRO if v == 0 else COLOR_SECUNDARIO for v in df["Bono_Total"]]
    fig = go.Figure(go.Bar(x=df["ID_Periodo"], y=df["Bono_Total"], marker_color=colores,
                             text=[f"${v:,.0f}" if v > 0 else "Sin bono" for v in df["Bono_Total"]],
                             textposition="outside"))
    fig.update_layout(
        title={"text": "EVOLUCION MENSUAL DEL BONO TOTAL OFICIAL DEL PROMOTOR",
               "font": {"size": 13, "color": COLOR_PRIMARIO}},
        template=PLANTILLA_PLOTLY, height=340, font_family=FUENTE,
        margin=dict(l=10, r=10, t=50, b=10), yaxis_title="Bono Total ($)")
    return fig


def interpretacion_bono_total_mensual(resumen_bonos: pd.DataFrame) -> str:
    if resumen_bonos is None or resumen_bonos.empty:
        return "Sin historico suficiente para interpretar el comportamiento del bono todavia."
    df = resumen_bonos.sort_values("ID_Periodo")
    ultimo = df.iloc[-1]
    bono_val = ultimo.get("Bono_Total", 0) or 0
    meses_en_cero = (df["Bono_Total"].tail(3) == 0).sum() if len(df) >= 1 else 0
    if bono_val == 0:
        texto = f"El promotor no genero bono oficial en el periodo mas reciente ({ultimo['ID_Periodo']})."
        if meses_en_cero >= 2:
            texto += (f" Este es el {int(meses_en_cero)}º mes consecutivo en $0 dentro de los ultimos "
                      f"tres periodos analizados, lo cual representa una perdida sostenida de ingresos "
                      f"recurrentes que el director deberia investigar directamente con SMNYL.")
        return texto
    if len(df) >= 2:
        anterior = df.iloc[-2].get("Bono_Total", 0) or 0
        if anterior == 0:
            return (f"El promotor genero ${bono_val:,.2f} en el periodo mas reciente, recuperando el "
                    f"bono despues de un mes sin generarlo. Conviene dar seguimiento para confirmar si "
                    f"la recuperacion se sostiene.")
        variacion_pct = ((bono_val - anterior) / anterior * 100) if anterior else 0
        direccion = "un aumento" if variacion_pct > 0 else "una disminucion"
        return (f"El bono total del periodo mas reciente fue de ${bono_val:,.2f}, lo que representa "
                f"{direccion} de {abs(variacion_pct):.1f}% respecto al mes anterior (${anterior:,.2f}).")
    return f"El bono total del periodo mas reciente fue de ${bono_val:,.2f}."


def grafica_composicion_bonos(resumen_bonos: pd.DataFrame):
    if resumen_bonos is None or resumen_bonos.empty:
        return _figura_vacia("Sin datos.")
    ultimo = resumen_bonos.sort_values("ID_Periodo").iloc[-1]
    conceptos = ["Bono_Vida", "Bono_GMMI", "Bono_Beneficios", "Subsidio_Renta",
                 "Bono_Conexion", "Bono_Desarrollo", "Bono_Crecimiento"]
    pares = [(c.replace("_", " "), ultimo.get(c, 0) or 0) for c in conceptos]
    # Se excluyen los conceptos en $0 -- de lo contrario sus etiquetas se
    # amontonan en un solo punto del donut y quedan ilegibles.
    pares_con_valor = [(etq, val) for etq, val in pares if val > 0]
    if not pares_con_valor:
        return _figura_vacia("Sin bonos pagados este periodo (todos los conceptos en $0).")
    etiquetas = [p[0] for p in pares_con_valor]
    valores = [p[1] for p in pares_con_valor]
    fig = go.Figure(go.Pie(labels=etiquetas, values=valores, hole=0.45,
                             marker=dict(colors=px.colors.sequential.Blues_r)))
    fig.update_layout(
        title={"text": "COMPOSICION DEL BONO TOTAL DEL MES POR CONCEPTO OFICIAL",
               "font": {"size": 12.5, "color": COLOR_PRIMARIO}, "x": 0, "xanchor": "left"},
        template=PLANTILLA_PLOTLY, height=360, font_family=FUENTE,
        margin=dict(l=10, r=10, t=70, b=10))
    return fig


def interpretacion_composicion_bonos(resumen_bonos: pd.DataFrame) -> str:
    if resumen_bonos is None or resumen_bonos.empty:
        return "Sin datos suficientes para interpretar la composicion del bono."
    ultimo = resumen_bonos.sort_values("ID_Periodo").iloc[-1]
    conceptos = {"Bono Vida": ultimo.get("Bono_Vida", 0) or 0, "Bono GMMI": ultimo.get("Bono_GMMI", 0) or 0,
                 "Bono Beneficios": ultimo.get("Bono_Beneficios", 0) or 0, "Subsidio Renta": ultimo.get("Subsidio_Renta", 0) or 0,
                 "Bono Conexion": ultimo.get("Bono_Conexion", 0) or 0, "Bono Desarrollo": ultimo.get("Bono_Desarrollo", 0) or 0,
                 "Bono Crecimiento": ultimo.get("Bono_Crecimiento", 0) or 0}
    total = sum(conceptos.values())
    if total == 0:
        return "Ningun concepto de bono genero ingreso durante el periodo mas reciente."
    concepto_principal = max(conceptos, key=conceptos.get)
    pct_principal = conceptos[concepto_principal] / total * 100
    return (f"El bono total del periodo mas reciente se compone principalmente de {concepto_principal}, "
            f"que representa {pct_principal:.1f}% del total (${conceptos[concepto_principal]:,.2f} de "
            f"${total:,.2f}). Financieramente, esto indica en que concepto de bono se concentra el "
            f"ingreso del promotor, informacion util para anticipar la sensibilidad del ingreso ante "
            f"cambios en ese concepto especifico.")


def grafica_segmentacion(segmentacion: pd.DataFrame):
    if segmentacion is None or segmentacion.empty or "Segmento" not in segmentacion.columns:
        return _figura_vacia("Sin datos suficientes para segmentar todavia.")
    conteo = segmentacion["Segmento"].value_counts().reset_index()
    conteo.columns = ["Segmento", "Cantidad"]
    colores = [PALETA_SEGMENTOS.get(s, COLOR_NEUTRO) for s in conteo["Segmento"]]
    fig = go.Figure(go.Pie(labels=conteo["Segmento"], values=conteo["Cantidad"], hole=0.45,
                             marker=dict(colors=colores)))
    fig.update_layout(
        title={"text": "DISTRIBUCION DE ASESORES SEGUN EL INDICE DE SALUD DEL NEGOCIO",
               "font": {"size": 13, "color": COLOR_PRIMARIO}},
        template=PLANTILLA_PLOTLY, height=340, font_family=FUENTE,
        margin=dict(l=10, r=10, t=50, b=10))
    return fig


def interpretacion_segmentacion(segmentacion: pd.DataFrame) -> str:
    if segmentacion is None or segmentacion.empty or "Segmento" not in segmentacion.columns:
        return "Sin datos suficientes para interpretar la segmentacion todavia."
    conteo = segmentacion["Segmento"].value_counts()
    total = conteo.sum()
    riesgo_alto = conteo.get("Riesgo alto", 0)
    riesgo_medio = conteo.get("Riesgo medio", 0)
    pct_riesgo = (riesgo_alto + riesgo_medio) / total * 100 if total else 0
    return (f"De {int(total)} asesores evaluados en el periodo mas reciente, {int(riesgo_alto)} se "
            f"clasifican en Riesgo Alto y {int(riesgo_medio)} en Riesgo Medio segun el Indice de Salud "
            f"del Negocio, lo que representa {pct_riesgo:.1f}% de la fuerza de ventas en alguna condicion "
            f"de riesgo. El director deberia priorizar conversaciones de desarrollo con los asesores en "
            f"Riesgo Alto, dado que combinan baja produccion con deterioro en LIMRA o IGC.")


def grafica_real_vs_plan(real_vs_plan: pd.DataFrame):
    if real_vs_plan is None or real_vs_plan.empty:
        return _figura_vacia("Sin datos.")
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Meta prorrateada", x=real_vs_plan["Indicador"],
                          y=real_vs_plan["Meta_Prorrateada"], marker_color=COLOR_NEUTRO))
    fig.add_trace(go.Bar(name="Real", x=real_vs_plan["Indicador"],
                          y=real_vs_plan["Real"], marker_color=COLOR_PRIMARIO))
    fig.update_layout(
        title={"text": "AVANCE REAL DE YAKOL CONTRA LA META ANUAL PRORRATEADA AL MES EN CURSO",
               "font": {"size": 12.5, "color": COLOR_PRIMARIO}, "x": 0, "xanchor": "left", "y": 0.97},
        barmode="group", template=PLANTILLA_PLOTLY, height=380, font_family=FUENTE,
        margin=dict(l=10, r=10, t=95, b=10),
        legend=dict(orientation="h", yanchor="top", y=0.90, x=0, xanchor="left"))
    return fig


def interpretacion_real_vs_plan(real_vs_plan: pd.DataFrame) -> str:
    if real_vs_plan is None or real_vs_plan.empty:
        return "Sin datos suficientes para interpretar el avance contra la meta."
    partes = []
    for _, fila in real_vs_plan.iterrows():
        avance = fila.get("Avance_Pct")
        if avance is None:
            continue
        estado = "por encima" if avance >= 100 else ("cerca de" if avance >= 90 else "por debajo")
        partes.append(f"{fila['Indicador']} avanza al {avance:.1f}% de su meta prorrateada, {estado} del ritmo esperado")
    if not partes:
        return "Sin datos suficientes para interpretar el avance contra la meta."
    return ("En el periodo mas reciente, " + "; ".join(partes) + ". El director deberia dar seguimiento "
            "prioritario al indicador con menor porcentaje de avance, dado que es el que mas riesgo "
            "representa para el cumplimiento de la meta anual.")


def grafica_flujo_simplificado(resumen_bonos: pd.DataFrame, costeo_asesores: pd.DataFrame,
                                 otros_ingresos: float = 0.0):
    """Grafica UNICA e integrada de ingresos vs. egresos y flujo neto -- no
    existe una tabla separada en ningun otro lugar de la aplicacion, esta
    grafica es la unica fuente de esta informacion.

    INGRESOS TOTALES = Bono Total oficial + Otros ingresos (captura manual)
    FLUJO NETO SIMPLIFICADO = INGRESOS TOTALES - EGRESOS TOTALES

    No es un estado de flujo de efectivo contable completo -- el sistema no
    cuenta con ese nivel de detalle (nomina general, renta y demas ya estan
    incluidos dentro de Egresos Totales via el presupuesto real, pero no se
    desglosan aqui)."""
    if resumen_bonos is None or resumen_bonos.empty:
        return _figura_vacia("Sin datos.")
    ultimo = resumen_bonos.sort_values("ID_Periodo").iloc[-1]
    bono = ultimo.get("Bono_Total", 0) or 0
    otros_ingresos = otros_ingresos or 0.0
    ingresos_totales = bono + otros_ingresos
    egresos_totales = 0.0
    if costeo_asesores is not None and not costeo_asesores.empty:
        fila_total = costeo_asesores[costeo_asesores["Concepto"] == "COSTO TOTAL DEL MES"]
        if len(fila_total):
            try:
                egresos_totales = float(fila_total["Monto"].iloc[0])
            except (ValueError, TypeError):
                egresos_totales = 0.0
    flujo_neto = ingresos_totales - egresos_totales
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative", "relative", "relative", "total"],
        x=["Bono Total", "Otros Ingresos", "Egresos Totales", "Flujo Neto Simplificado"],
        y=[bono, otros_ingresos, -egresos_totales, flujo_neto],
        connector={"line": {"color": COLOR_NEUTRO}},
        increasing={"marker": {"color": COLOR_EXITO}},
        decreasing={"marker": {"color": COLOR_PELIGRO}},
        totals={"marker": {"color": COLOR_PRIMARIO}},
        text=[f"${bono:,.0f}", f"${otros_ingresos:,.0f}", f"-${egresos_totales:,.0f}", f"${flujo_neto:,.0f}"],
        textposition="outside",
    ))
    fig.update_layout(
        title={"text": "COMPARATIVO MENSUAL ENTRE INGRESOS TOTALES Y EGRESOS DE YAKOL",
               "font": {"size": 13, "color": COLOR_PRIMARIO}},
        template=PLANTILLA_PLOTLY, height=360, font_family=FUENTE,
        margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    return fig, ingresos_totales, egresos_totales, flujo_neto


def interpretacion_flujo(resumen_bonos: pd.DataFrame, ingresos_totales: float,
                          egresos_totales: float, flujo_neto: float, otros_ingresos: float) -> str:
    if resumen_bonos is None or resumen_bonos.empty:
        return "Sin datos suficientes para interpretar el flujo del mes."
    ultimo = resumen_bonos.sort_values("ID_Periodo").iloc[-1]
    bono = ultimo.get("Bono_Total", 0) or 0
    partes = [f"Los ingresos totales del periodo mas reciente suman ${ingresos_totales:,.2f}, "
              f"compuestos por ${bono:,.2f} de bono oficial"]
    if otros_ingresos > 0:
        partes.append(f" y ${otros_ingresos:,.2f} de otros ingresos capturados manualmente")
    partes.append(f". Los egresos totales, correspondientes al costo de reclutamiento del mes, "
                   f"ascienden a ${egresos_totales:,.2f}.")
    if flujo_neto < 0:
        partes.append(f" El flujo neto simplificado es NEGATIVO (${flujo_neto:,.2f}), lo que significa "
                       f"que el gasto de reclutamiento del mes no fue cubierto por los ingresos del "
                       f"periodo. El director deberia evaluar si esta situacion es temporal o recurrente.")
    else:
        partes.append(f" El flujo neto simplificado es POSITIVO (${flujo_neto:,.2f}), lo que significa "
                       f"que los ingresos del periodo cubrieron el costo de reclutamiento del mes.")
    return "".join(partes)


def grafica_destacados_dispersion(segmentacion: pd.DataFrame, destacados: pd.DataFrame):
    """Contraparte visual de grafica_segmentacion: en vez de mostrar la
    distribucion de bandas, posiciona a cada asesor evaluado en un plano de
    produccion (Polizas de Vida promedio) contra margen de cumplimiento
    normativo (LIMRA/IGC promedio menos el minimo oficial), resaltando a
    los que calificaron como destacados."""
    if segmentacion is None or segmentacion.empty or "Indice_Salud_Negocio" not in segmentacion.columns:
        return _figura_vacia("Sin datos suficientes todavia.")

    resumen = segmentacion.groupby("ID_Asesor").agg(
        Produccion_Vida=("Polizas_Vida", "mean"),
        LIMRA_Prom=("LIMRA_Indice_Real", "mean"),
        IGC_Prom=("IGC_Indice_Real", "mean"),
    ).reset_index()
    resumen = resumen.dropna(subset=["Produccion_Vida"])
    if resumen.empty:
        return _figura_vacia("Sin datos suficientes todavia.")
    resumen["Margen_Cumplimiento"] = ((resumen["LIMRA_Prom"] - UMBRAL_LIMRA) +
                                       (resumen["IGC_Prom"] - UMBRAL_IGC)) / 2

    ids_destacados = set(destacados["ID_Asesor"]) if destacados is not None and not destacados.empty else set()
    resumen["Es_Destacado"] = resumen["ID_Asesor"].isin(ids_destacados)
    resto, top = resumen[~resumen["Es_Destacado"]], resumen[resumen["Es_Destacado"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=resto["Produccion_Vida"], y=resto["Margen_Cumplimiento"], mode="markers",
        marker=dict(color=COLOR_NEUTRO, size=9, opacity=0.55),
        name="Resto de la fuerza de ventas",
        text=resto["ID_Asesor"], hovertemplate="Asesor %{text}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=top["Produccion_Vida"], y=top["Margen_Cumplimiento"], mode="markers",
        marker=dict(color=COLOR_EXITO, size=13, line=dict(width=1.5, color="white")),
        name="Asesores destacados",
        text=top["ID_Asesor"], hovertemplate="Asesor %{text}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=COLOR_NEUTRO, opacity=0.6,
                   annotation_text="Margen 0 = justo en el minimo normativo", annotation_position="bottom right",
                   annotation_font_size=10)
    fig.update_layout(
        title={"text": "PRODUCCION PROMEDIO DE VIDA VS. MARGEN DE CUMPLIMIENTO NORMATIVO, POR ASESOR",
               "font": {"size": 12.5, "color": COLOR_PRIMARIO}, "x": 0, "xanchor": "left", "y": 0.97},
        template=PLANTILLA_PLOTLY, height=400, font_family=FUENTE,
        margin=dict(l=10, r=10, t=95, b=10),
        xaxis_title="Polizas de Vida promedio por periodo", yaxis_title="Margen sobre minimos LIMRA/IGC",
        legend=dict(orientation="h", yanchor="top", y=0.90, x=0, xanchor="left"))
    return fig


def interpretacion_destacados_dispersion(destacados: pd.DataFrame) -> str:
    if destacados is None or destacados.empty:
        return ("Con la informacion disponible, ningun asesor supera todavia el umbral definido para "
                "calificar como destacado (Indice de Salud del Negocio promedio de 80 o mas, con "
                "antiguedad y produccion minimas).")
    lider = destacados.iloc[0]
    return (f"{len(destacados)} asesor(es) califican como destacados con el historico disponible. "
            f"El de mejor desempeno es {lider['Nombre']}, con un Indice de Desempeno Destacado de "
            f"{lider['Indice_Desempeno_Destacado']:.1f}: sostiene un promedio de "
            f"{lider['Promedio_Indice_Salud']:.1f} en el Indice de Salud del Negocio durante "
            f"{lider['Periodos_Evaluados']} periodo(s), con {lider['Consistencia_Pct']:.0f}% del "
            f"tiempo en banda alta.")


def grafica_contribucion_variables(fila_asesor: pd.Series):
    """Barra horizontal con los puntos que cada una de las 6 variables del
    Indice de Salud del Negocio aporto al resultado final de un asesor
    especifico (columnas Puntos_* de Segmentacion_Asesores). Coloreada por
    el nivel alcanzado en cada variable -- nunca recalcula nada, solo
    visualiza lo que analitica_avanzada.py ya calculo."""
    variables = list(_ETIQUETAS_VARIABLE.keys())
    puntos = [fila_asesor.get(f"Puntos_{v}") for v in variables]
    niveles = [fila_asesor.get(f"Nivel_{v}", "No evaluable") for v in variables]
    etiquetas = [_ETIQUETAS_VARIABLE[v] for v in variables]

    disponibles = [(e, p, n) for e, p, n in zip(etiquetas, puntos, niveles) if pd.notna(p)]
    if not disponibles:
        return _figura_vacia("Sin datos suficientes para este asesor todavia.")
    etiquetas_d, puntos_d, niveles_d = zip(*disponibles)
    colores = [NIVEL_COLOR.get(n, COLOR_NEUTRO) for n in niveles_d]

    orden = sorted(range(len(puntos_d)), key=lambda i: puntos_d[i])
    etiquetas_o = [etiquetas_d[i] for i in orden]
    puntos_o = [puntos_d[i] for i in orden]
    colores_o = [colores[i] for i in orden]
    niveles_o = [niveles_d[i] for i in orden]

    fig = go.Figure(go.Bar(
        x=puntos_o, y=etiquetas_o, orientation="h", marker_color=colores_o,
        text=[f"{p:.1f} pts ({n})" for p, n in zip(puntos_o, niveles_o)], textposition="outside",
    ))
    fig.update_layout(
        title={"text": "PUNTOS APORTADOS AL INDICE DE SALUD, POR VARIABLE",
               "font": {"size": 12.5, "color": COLOR_PRIMARIO}, "x": 0, "xanchor": "left"},
        template=PLANTILLA_PLOTLY, height=320, font_family=FUENTE,
        margin=dict(l=10, r=10, t=50, b=10), xaxis_title="Puntos aportados (de 25 / 15 / 10 maximos segun el peso)",
        showlegend=False)
    return fig


def interpretacion_contribucion_variables(fila_asesor: pd.Series) -> str:
    variables = list(_ETIQUETAS_VARIABLE.keys())
    pares = [(v, fila_asesor.get(f"Puntos_{v}"), fila_asesor.get(f"Nivel_{v}", "No evaluable"))
             for v in variables if pd.notna(fila_asesor.get(f"Puntos_{v}"))]
    if not pares:
        return "Sin datos suficientes para explicar la contribucion por variable todavia."
    mejor = max(pares, key=lambda p: p[1])
    peor = min(pares, key=lambda p: p[1])
    nombre = fila_asesor.get("Nombre_Asesor") or f"Asesor {fila_asesor.get('ID_Asesor', '')}"
    texto = (f"La variable que mas aporto al Indice de Salud de {nombre} fue "
             f"{_ETIQUETAS_VARIABLE[mejor[0]]} ({mejor[1]:.1f} puntos, nivel {mejor[2]}).")
    if peor[0] != mejor[0]:
        texto += (f" La que menos aporto fue {_ETIQUETAS_VARIABLE[peor[0]]} "
                  f"({peor[1]:.1f} puntos, nivel {peor[2]}).")
    return texto


def gauge_semaforo(valor, titulo, umbral_bajo, umbral_alto, invertido=False):
    """Gauge tipo velocimetro para un semaforo financiero. Si invertido=True,
    valores altos son MALOS (ej. % de incumplimiento)."""
    if invertido:
        color = COLOR_EXITO if valor <= umbral_bajo else (COLOR_ADVERTENCIA if valor <= umbral_alto else COLOR_PELIGRO)
    else:
        color = COLOR_PELIGRO if valor <= umbral_bajo else (COLOR_ADVERTENCIA if valor <= umbral_alto else COLOR_EXITO)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
        title={"text": titulo, "font": {"size": 13, "color": COLOR_PRIMARIO}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "bgcolor": "white",
            "steps": [
                {"range": [0, umbral_bajo], "color": "#F4F7FB"},
                {"range": [umbral_bajo, umbral_alto], "color": "#EDEFF3"},
                {"range": [umbral_alto, 100], "color": "#E2E8F0"},
            ],
        },
    ))
    fig.update_layout(template=PLANTILLA_PLOTLY, height=220, font_family=FUENTE,
                       margin=dict(l=20, r=20, t=40, b=10))
    return fig
