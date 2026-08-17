"""
hallazgos.py -- Motor de Resultados y Recomendaciones
------------------------------------------------------------
Genera hallazgos financieros y estrategicos leyendo UNICAMENTE los
DataFrames que el sistema ya calculo (nunca inventa cifras ni tendencias
que no esten sustentadas en los datos reales del periodo procesado). Cada
hallazgo indica de que hoja/calculo proviene, para que sea auditable.
"""

import pandas as pd

from config import UMBRAL_IGC, UMBRAL_LIMRA


def clasificar_asesores_en_riesgo(comparativo: pd.DataFrame, segmentacion: pd.DataFrame) -> pd.DataFrame:
    """Construye el detalle personalizado de asesores en riesgo real
    (Incumple_Real_LIMRA o Incumple_Real_IGC). El nivel alto/medio/bajo NO
    proviene del Cuaderno de Concursos -- es una regla propia, declarada
    aqui explicitamente, basada en que tan lejos esta el indicador de su
    minimo oficial:
      - Riesgo Alto: falla en ambos indicadores, o falla uno con una
        brecha de 10 puntos o mas respecto al minimo.
      - Riesgo Medio: falla un indicador con brecha de 3 a 10 puntos.
      - Riesgo Bajo: falla un indicador con brecha menor a 3 puntos.
    """
    if comparativo is None or comparativo.empty:
        return pd.DataFrame()
    ultimo_periodo = comparativo["ID_Periodo"].max()
    sub = comparativo[comparativo["ID_Periodo"] == ultimo_periodo].copy()
    en_riesgo = sub[sub["Incumple_Real_LIMRA"].isin([True, "VERDADERO"]) |
                     sub["Incumple_Real_IGC"].isin([True, "VERDADERO"])]
    if en_riesgo.empty:
        return pd.DataFrame()

    prod_por_asesor = {}
    if segmentacion is not None and not segmentacion.empty:
        sub_seg = segmentacion[segmentacion["ID_Periodo"] == ultimo_periodo]
        prod_por_asesor = sub_seg.set_index("ID_Asesor")[["Polizas_Vida", "Prima_Vida"]].to_dict("index")

    filas = []
    for _, r in en_riesgo.iterrows():
        falla_limra = r["Incumple_Real_LIMRA"] in (True, "VERDADERO")
        falla_igc = r["Incumple_Real_IGC"] in (True, "VERDADERO")
        limra_val, igc_val = r["LIMRA_Indice_Real"], r["IGC_Indice_Real"]

        brecha_limra = (UMBRAL_LIMRA - limra_val) if (falla_limra and pd.notna(limra_val)) else 0
        brecha_igc = (UMBRAL_IGC - igc_val) if (falla_igc and pd.notna(igc_val)) else 0
        brecha_max = max(brecha_limra, brecha_igc)

        if falla_limra and falla_igc:
            nivel = "Riesgo Alto"
        elif brecha_max >= 10:
            nivel = "Riesgo Alto"
        elif brecha_max >= 3:
            nivel = "Riesgo Medio"
        else:
            nivel = "Riesgo Bajo"

        indicadores = []
        if falla_limra:
            indicadores.append(f"LIMRA {limra_val:.2f}% (referencia minima: {UMBRAL_LIMRA:.2f}%)")
        if falla_igc:
            indicadores.append(f"IGC {igc_val:.2f}% (referencia minima: {UMBRAL_IGC:.2f}%)")

        prod = prod_por_asesor.get(r["ID_Asesor"], {})
        polizas = prod.get("Polizas_Vida")
        prima = prod.get("Prima_Vida")
        datos_produccion = ""
        if polizas is not None and pd.notna(polizas):
            datos_produccion = f"durante el periodo registro {polizas:.0f} poliza(s) de vida"
            if prima is not None and pd.notna(prima):
                datos_produccion += f" y un primaje de ${prima:,.2f}, mientras que "
            else:
                datos_produccion += ", mientras que "
        else:
            datos_produccion = "no se registro produccion de polizas de vida en el periodo, y "

        partes_indicador = []
        if falla_limra:
            partes_indicador.append(f"LIMRA se ubico en {limra_val:.2f}%, por debajo del nivel de "
                                     f"referencia de {UMBRAL_LIMRA:.2f}%")
        elif pd.notna(limra_val):
            partes_indicador.append(f"su LIMRA de {limra_val:.2f}% se encuentra por encima del minimo "
                                     f"de {UMBRAL_LIMRA:.2f}%")
        if falla_igc:
            partes_indicador.append(f"su IGC de {igc_val:.2f}% se encuentra por debajo del minimo "
                                     f"establecido de {UMBRAL_IGC:.2f}%")
        elif pd.notna(igc_val):
            partes_indicador.append(f"su IGC de {igc_val:.2f}% se encuentra por encima del minimo "
                                     f"establecido de {UMBRAL_IGC:.2f}%")

        explicacion = (
            f"El asesor {r['ID_Asesor']}, {r['Nombre_Asesor']}, se clasifica como {nivel.lower()} "
            f"debido a que {datos_produccion}{'; '.join(partes_indicador)}."
        )

        filas.append({
            "Numero de Asesor": r["ID_Asesor"], "Nombre": r["Nombre_Asesor"], "Nivel de Riesgo": nivel,
            "Indicadores que Influyeron": " | ".join(indicadores),
            "Explicacion Especifica": explicacion,
        })

    orden = {"Riesgo Alto": 0, "Riesgo Medio": 1, "Riesgo Bajo": 2}
    return pd.DataFrame(filas).sort_values(by="Nivel de Riesgo", key=lambda s: s.map(orden))


def _seguro(valor, default=0):
    try:
        if pd.isna(valor):
            return default
    except (TypeError, ValueError):
        pass
    return valor if valor is not None else default


def generar_hallazgos(resumen_bonos, comparativo, segmentacion, alertas_anomalias,
                       real_vs_plan, costeo_asesores, roi_campanas, hist_traspasos):
    """Cada hallazgo se expone con 4 campos separados -- hallazgo, evidencia,
    impacto, recomendacion -- para que la interfaz los muestre claramente
    diferenciados. Las condiciones de deteccion (los mismos umbrales y
    comparaciones de siempre) no cambiaron, solo la forma en que se redacta
    y estructura el resultado."""
    hallazgos = []

    # ------------------------------------------------------------------
    # RIESGOS
    # ------------------------------------------------------------------
    if resumen_bonos is not None and len(resumen_bonos) >= 2:
        df = resumen_bonos.sort_values("ID_Periodo")
        ultimo, anterior = df.iloc[-1], df.iloc[-2]
        if _seguro(ultimo["Bono_Total"]) == 0 and _seguro(anterior["Bono_Total"]) > 0:
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Bonos",
                "titulo": "Caida del Bono Total del Promotor",
                "hallazgo": "El Bono Total oficial del promotor paso de generar ingreso a $0 de un mes a otro.",
                "evidencia": f"Bono Total: ${anterior['Bono_Total']:,.0f} en {anterior['ID_Periodo']} "
                             f"contra $0 en {ultimo['ID_Periodo']}, segun Resumen_Bonos.",
                "impacto": "Perdida directa de un ingreso recurrente para la promotoria, con efecto "
                           "inmediato en el flujo neto simplificado del mes.",
                "recomendacion": "Investigar la causa directamente con SMNYL o con el equipo de "
                                 "reclutamiento antes de tomar cualquier accion comercial correctiva.",
            })
        primeros_no_cero = df[df["Bono_Total"] > 0]
        if len(primeros_no_cero) >= 1 and _seguro(ultimo["Bono_Total"]) == 0 and len(df) - len(primeros_no_cero) >= 3:
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Bonos",
                "titulo": "Bono Total en $0 por multiples periodos consecutivos",
                "hallazgo": "El Bono Total del promotor lleva varios meses consecutivos en $0.",
                "evidencia": f"De los {len(df)} periodos con historico disponible, {len(df) - len(primeros_no_cero)} "
                             f"registran Bono Total de $0, incluyendo el periodo mas reciente.",
                "impacto": "El impacto financiero acumulado de esta perdida de ingreso es significativo "
                           "para la rentabilidad de la promotoria si la tendencia continua.",
                "recomendacion": "Escalar el caso con SMNYL como prioridad, dado que ya no se trata de "
                                 "una variacion aislada de un solo mes.",
            })

    if comparativo is not None and not comparativo.empty:
        cronicos = comparativo[
            (comparativo["Incumple_Real_IGC"] .isin([True, "VERDADERO"])) | (comparativo["Incumple_Real_LIMRA"] .isin([True, "VERDADERO"]))
        ]
        if len(cronicos):
            conteo_por_asesor = cronicos.groupby("ID_Asesor").size()
            total_periodos = comparativo["ID_Periodo"].nunique()
            cronicos_reales = conteo_por_asesor[conteo_por_asesor == total_periodos]
            if len(cronicos_reales) > 0 and total_periodos >= 3:
                nombres = comparativo[comparativo["ID_Asesor"].isin(cronicos_reales.index)]["Nombre_Asesor"].unique()
                hallazgos.append({
                    "tipo": "riesgo", "modulo": "Cumplimiento",
                    "titulo": f"{len(cronicos_reales)} asesor(es) en incumplimiento sistematico",
                    "hallazgo": f"{len(cronicos_reales)} asesor(es) incumplieron IGC y/o LIMRA en TODOS "
                                f"los periodos disponibles, fuera de la rampa de proteccion por antiguedad.",
                    "evidencia": f"Asesores: {', '.join(nombres[:5])}{'...' if len(nombres) > 5 else ''}. "
                                 f"Incumplimiento sostenido durante los {total_periodos} periodos con historico.",
                    "impacto": "Sugiere un problema estructural de desempeno en estos asesores, no una "
                               "variacion aislada, con riesgo de continuar afectando el IGC/LIMRA del promotor.",
                    "recomendacion": "Plan de seguimiento mensual especifico para estos asesores, con "
                                     "metas verificables a traves del propio sistema, en vez de una "
                                     "politica general para toda la fuerza de ventas.",
                })
        ultimo_periodo = comparativo["ID_Periodo"].max()
        sub = comparativo[comparativo["ID_Periodo"] == ultimo_periodo]
        limra_cerca = sub[(sub["LIMRA_Indice_Real"] >= UMBRAL_LIMRA) & (sub["LIMRA_Indice_Real"] < UMBRAL_LIMRA + 1.5)]
        if len(limra_cerca) > 0:
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Cumplimiento",
                "titulo": "LIMRA del promotor con poco margen sobre el umbral normativo",
                "hallazgo": f"{len(limra_cerca)} asesor(es) tienen LIMRA apenas por encima del minimo normativo.",
                "evidencia": f"LIMRA entre {UMBRAL_LIMRA:.2f}% y {UMBRAL_LIMRA + 1.5:.2f}% "
                             f"(minimo oficial: {UMBRAL_LIMRA:.2f}%), sin margen de holgura.",
                "impacto": "Una variacion adversa pequena en persistencia podria hacerlos caer en "
                           "incumplimiento real el proximo mes.",
                "recomendacion": "Dar seguimiento preventivo a estos asesores antes de que crucen el "
                                 "umbral, en vez de esperar a que el incumplimiento ya sea real.",
            })

    if alertas_anomalias is not None and not alertas_anomalias.empty:
        conteo_asesor = alertas_anomalias.groupby("ID_Asesor").size().sort_values(ascending=False)
        if len(conteo_asesor) and conteo_asesor.iloc[0] >= 3:
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Anomalias",
                "titulo": "Concentracion de movimientos atipicos en un solo asesor",
                "hallazgo": "Un asesor concentra un numero desproporcionado de movimientos de cartera atipicos.",
                "evidencia": f"El asesor con clave {conteo_asesor.index[0]} concentra {conteo_asesor.iloc[0]} "
                             f"alertas de anomalias en el historico disponible.",
                "impacto": "Puede reflejar una estrategia deliberada de consolidacion de cartera, o bien "
                           "una situacion que amerite revision bajo las reglas de Fair Play.",
                "recomendacion": "Revisar directamente con este asesor el origen de dichos movimientos "
                                 "antes de asumir alguna de las dos causas.",
            })

    if hist_traspasos is not None and len(hist_traspasos) >= 10:
        por_periodo = hist_traspasos.groupby("ID_Periodo").size().sort_index()
        if len(por_periodo) >= 3 and por_periodo.iloc[-1] > por_periodo.iloc[0] * 2:
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Traspasos",
                "titulo": "Crecimiento acelerado en el volumen de traspasos",
                "hallazgo": "El volumen de traspasos de cartera crecio de forma acelerada en el historico disponible.",
                "evidencia": f"De {por_periodo.iloc[0]} a {por_periodo.iloc[-1]} movimientos entre el "
                             f"primer y el ultimo periodo disponible -- mas del doble.",
                "impacto": "Un crecimiento acelerado y sostenido puede reflejar friccion interna en la "
                           "asignacion de cartera entre asesores.",
                "recomendacion": "Dar seguimiento al origen de este crecimiento, identificando si se "
                                 "concentra en pocos asesores o esta distribuido de forma pareja.",
            })

    # ------------------------------------------------------------------
    # OPORTUNIDADES
    # ------------------------------------------------------------------
    if segmentacion is not None and not segmentacion.empty and "Segmento" in segmentacion.columns:
        ultimo_periodo = segmentacion["ID_Periodo"].max()
        sub = segmentacion[segmentacion["ID_Periodo"] == ultimo_periodo]
        alto = sub[sub["Segmento"] == "Alto desempeno"]
        if len(alto) > 0:
            hallazgos.append({
                "tipo": "oportunidad", "modulo": "Segmentacion",
                "titulo": f"{len(alto)} asesor(es) de alto desempeno identificados",
                "hallazgo": f"{len(alto)} asesor(es) muestran la mejor combinacion de calidad de "
                            f"cartera y produccion segun el Indice de Salud del Negocio.",
                "evidencia": "Clasificacion 'Alto desempeno' (banda 80-89.99 del Indice de Salud del "
                             "Negocio) en el periodo mas reciente.",
                "impacto": "Representan el activo comercial de mayor calidad de la promotoria en este momento.",
                "recomendacion": "Considerarlos como candidatos naturales para roles de mentoria "
                                 "(Asesor Desarrollador) o para campanas de reconocimiento que "
                                 "refuercen su permanencia.",
            })
        riesgo_alto = sub[sub["Segmento"] == "Riesgo alto"]
        if len(riesgo_alto) > 0:
            nombres = ", ".join(riesgo_alto["ID_Asesor"].astype(str).unique()[:5])
            hallazgos.append({
                "tipo": "riesgo", "modulo": "Indice de Salud del Negocio",
                "titulo": f"{len(riesgo_alto)} asesor(es) en Riesgo Alto segun el Indice de Salud del Negocio",
                "hallazgo": f"{len(riesgo_alto)} asesor(es) se clasifican en Riesgo Alto, combinando "
                            f"polizas, prima, LIMRA e IGC ponderados.",
                "evidencia": f"Claves: {nombres}. Incluye las reglas de control del modelo (cero "
                             f"produccion de Vida o deterioro severo en LIMRA/IGC limitan la "
                             f"clasificacion aunque el promedio numerico sea mayor).",
                "impacto": "Representan el grupo de mayor riesgo comercial y normativo combinado "
                           "dentro de la fuerza de ventas actual.",
                "recomendacion": "Ver el detalle individual en la tabla de Analisis y Plan de "
                                 "Mitigacion del Riesgo por Asesor, con la accion especifica para cada caso.",
            })

    if real_vs_plan is not None and not real_vs_plan.empty:
        for _, fila in real_vs_plan.iterrows():
            avance = _seguro(fila.get("Avance_Pct"))
            if avance and avance >= 90:
                hallazgos.append({
                    "tipo": "oportunidad", "modulo": "Real vs. Plan",
                    "titulo": f"Meta de {fila['Indicador']} casi alcanzada",
                    "hallazgo": f"El avance real de {fila['Indicador']} esta muy cerca de la meta prorrateada a la fecha.",
                    "evidencia": f"Avance de {avance:.1f}% respecto a la meta prorrateada del periodo.",
                    "impacto": "A este ritmo, el indicador podria cerrar el ano dentro o cerca de la meta anual.",
                    "recomendacion": "Mantener el ritmo actual sin cambios adicionales; no requiere intervencion.",
                })

    # ------------------------------------------------------------------
    # RECOMENDACIONES GENERALES (derivadas de los hallazgos anteriores)
    # ------------------------------------------------------------------
    riesgos = [h for h in hallazgos if h["tipo"] == "riesgo"]
    if any(h["modulo"] == "Bonos" for h in riesgos):
        hallazgos.append({
            "tipo": "recomendacion", "modulo": "Bonos",
            "titulo": "Investigar la causa raiz de la caida de bonos con SMNYL",
            "hallazgo": "Se identificaron una o mas alertas relacionadas con el comportamiento del Bono Total.",
            "evidencia": "Ver el detalle en los hallazgos de riesgo del modulo Bonos, arriba en esta seccion.",
            "impacto": "Actuar sin confirmar la causa raiz puede llevar a una respuesta comercial "
                       "equivocada para el problema real.",
            "recomendacion": "Confirmar si la caida responde a un cambio en las reglas del concurso, "
                             "una reclasificacion de la promotoria, o una disminucion genuina de "
                             "actividad -- cada causa requiere una respuesta distinta.",
        })
    if any(h["modulo"] == "Cumplimiento" for h in riesgos):
        hallazgos.append({
            "tipo": "recomendacion", "modulo": "Cumplimiento",
            "titulo": "Plan de acompanamiento focalizado, no generico",
            "hallazgo": "Se identificaron asesores con incumplimiento normativo real o LIMRA con poco margen.",
            "evidencia": "Ver el detalle individual en la tabla de Analisis y Plan de Mitigacion del "
                         "Riesgo por Asesor.",
            "impacto": "Un plan generico para toda la fuerza de ventas diluye la atencion que "
                       "necesitan especificamente los casos identificados.",
            "recomendacion": "Implementar un plan de seguimiento mensual especifico para los asesores "
                             "identificados, con metas verificables a traves del propio sistema.",
        })
    if costeo_asesores is not None and not costeo_asesores.empty:
        fila = costeo_asesores[costeo_asesores["Concepto"] == "Costo promedio por asesor nuevo"]
        if len(fila) and isinstance(fila["Monto"].iloc[0], (int, float)):
            hallazgos.append({
                "tipo": "recomendacion", "modulo": "Costeo",
                "titulo": "Monitorear el costo de reclutamiento contra el ritmo real de incorporacion",
                "hallazgo": "El costo promedio por asesor nuevo depende directamente del ritmo de reclutamiento del mes.",
                "evidencia": f"Costo promedio de incorporar un asesor este periodo: ${fila['Monto'].iloc[0]:,.0f}.",
                "impacto": "Si el ritmo de reclutamiento se mantiene bajo, este costo unitario seguira "
                           "siendo alto, dado que los costos fijos no varian de forma proporcional.",
                "recomendacion": "Acelerar el reclutamiento diluye el costo fijo entre mas "
                                 "incorporaciones, reduciendo el costo promedio por asesor.",
            })

    if not hallazgos:
        hallazgos.append({
            "tipo": "recomendacion", "modulo": "General",
            "titulo": "Sin hallazgos relevantes este periodo",
            "hallazgo": "Con la informacion disponible, el sistema no detecto riesgos ni oportunidades "
                        "que superen los criterios de alerta definidos.",
            "evidencia": "No se cumplio ninguna de las condiciones de deteccion definidas en este modulo.",
            "impacto": "No aplica.",
            "recomendacion": "Continuar procesando meses adicionales; los hallazgos se enriqueceran "
                             "conforme se acumule mas historico.",
        })

    return hallazgos


def generar_plan_mitigacion_riesgo(comparativo: pd.DataFrame, segmentacion: pd.DataFrame) -> pd.DataFrame:
    """Tabla ANALISIS Y PLAN DE MITIGACION DEL RIESGO POR ASESOR. Reutiliza
    la misma clasificacion de clasificar_asesores_en_riesgo, agregando una
    accion de mitigacion especifica segun cual sea la causa identificada
    para cada asesor -- nunca la misma recomendacion para todos."""
    base = clasificar_asesores_en_riesgo(comparativo, segmentacion)
    if base.empty:
        return pd.DataFrame()

    ultimo_periodo = comparativo["ID_Periodo"].max()
    sub = comparativo[comparativo["ID_Periodo"] == ultimo_periodo].set_index("ID_Asesor")

    prod_por_asesor = {}
    if segmentacion is not None and not segmentacion.empty:
        sub_seg = segmentacion[segmentacion["ID_Periodo"] == ultimo_periodo]
        prod_por_asesor = sub_seg.set_index("ID_Asesor")[["Polizas_Vida"]].to_dict("index")

    filas = []
    for _, r in base.iterrows():
        id_asesor = r["Numero de Asesor"]
        datos = sub.loc[id_asesor] if id_asesor in sub.index else None
        if datos is None:
            continue
        falla_limra = datos["Incumple_Real_LIMRA"] in (True, "VERDADERO")
        falla_igc = datos["Incumple_Real_IGC"] in (True, "VERDADERO")
        limra_val, igc_val = datos["LIMRA_Indice_Real"], datos["IGC_Indice_Real"]
        polizas = prod_por_asesor.get(id_asesor, {}).get("Polizas_Vida")
        bajo_polizas = polizas is not None and pd.notna(polizas) and polizas == 0

        # Se genera una fila por CADA causa relevante identificada -- si un
        # asesor tiene mas de una causa, aparece mas de una vez, cada una
        # con su propia accion de mitigacion especifica.
        if bajo_polizas:
            filas.append({
                "Numero de Asesor": id_asesor, "Nombre": r["Nombre"], "Nivel de Riesgo": r["Nivel de Riesgo"],
                "Indicador que Genera el Riesgo": "Produccion (Polizas de Vida)",
                "Resultado Obtenido": "0 polizas de vida en el periodo",
                "Valor de Referencia": "N/A -- indicador de actividad, no normativo",
                "Motivo Especifico del Riesgo": f"El asesor {r['Nombre']} no registro ninguna poliza de "
                    f"vida durante el periodo mas reciente, lo cual afecta directamente su produccion "
                    f"y, en consecuencia, su clasificacion dentro del Indice de Salud del Negocio.",
                "Accion de Mitigacion Recomendada": "Enfocar la conversacion de desarrollo en "
                    "productividad y colocacion: revisar el embudo de prospeccion, numero de citas "
                    "agendadas y realizadas, y tasa de conversion a solicitud, para identificar en que "
                    "etapa se esta deteniendo el proceso comercial del asesor.",
            })
        if falla_limra:
            filas.append({
                "Numero de Asesor": id_asesor, "Nombre": r["Nombre"], "Nivel de Riesgo": r["Nivel de Riesgo"],
                "Indicador que Genera el Riesgo": "LIMRA",
                "Resultado Obtenido": f"{limra_val:.2f}%",
                "Valor de Referencia": f"{UMBRAL_LIMRA:.2f}% (minimo oficial)",
                "Motivo Especifico del Riesgo": f"El LIMRA de {r['Nombre']} se ubica en {limra_val:.2f}%, "
                    f"por debajo del minimo oficial de {UMBRAL_LIMRA:.2f}%, lo cual indica una perdida "
                    f"de persistencia en la cartera de nueva produccion (polizas emitidas en los "
                    f"primeros 25 meses).",
                "Accion de Mitigacion Recomendada": "Enfocar la conversacion en la condicion especifica "
                    "que afecta la persistencia de cartera nueva: revisar cancelaciones recientes, "
                    "calidad del perfilamiento inicial del cliente, y seguimiento de cobranza en los "
                    "primeros meses de la poliza.",
            })
        if falla_igc:
            filas.append({
                "Numero de Asesor": id_asesor, "Nombre": r["Nombre"], "Nivel de Riesgo": r["Nivel de Riesgo"],
                "Indicador que Genera el Riesgo": "IGC",
                "Resultado Obtenido": f"{igc_val:.2f}%",
                "Valor de Referencia": f"{UMBRAL_IGC:.2f}% (minimo oficial)",
                "Motivo Especifico del Riesgo": f"El IGC de {r['Nombre']} se ubica en {igc_val:.2f}%, por "
                    f"debajo del minimo oficial de {UMBRAL_IGC:.2f}%, lo cual indica una perdida de "
                    f"conservacion en la cartera ya madura (polizas de mas de 13 meses de emision).",
                "Accion de Mitigacion Recomendada": "Enfocar la conversacion en la calidad de "
                    "conservacion de la cartera madura: revisar motivos de cancelacion de polizas "
                    "antiguas, y evaluar si existe un patron de cobranza o de servicio postventa que "
                    "explique la perdida de persistencia a largo plazo.",
            })

    return pd.DataFrame(filas)


def calcular_semaforo_general(comparativo, resumen_bonos):
    """Clasifica el estado financiero general en Bajo/Medio/Alto riesgo,
    combinando cumplimiento normativo y tendencia de bonos -- una sola
    etiqueta resumen para el encabezado del dashboard."""
    puntos_riesgo = 0

    if comparativo is not None and not comparativo.empty:
        ultimo_periodo = comparativo["ID_Periodo"].max()
        sub = comparativo[comparativo["ID_Periodo"] == ultimo_periodo]
        n_incumple = ((sub["Incumple_Real_IGC"] .isin([True, "VERDADERO"])) | (sub["Incumple_Real_LIMRA"] .isin([True, "VERDADERO"]))).sum()
        pct_incumple = n_incumple / len(sub) if len(sub) else 0
        if pct_incumple > 0.15:
            puntos_riesgo += 2
        elif pct_incumple > 0.05:
            puntos_riesgo += 1

    if resumen_bonos is not None and len(resumen_bonos) >= 2:
        df = resumen_bonos.sort_values("ID_Periodo")
        if _seguro(df["Bono_Total"].iloc[-1]) == 0 and _seguro(df["Bono_Total"].iloc[-2]) == 0:
            puntos_riesgo += 2
        elif _seguro(df["Bono_Total"].iloc[-1]) == 0:
            puntos_riesgo += 1

    if puntos_riesgo >= 3:
        return "alto", "Riesgo Alto"
    elif puntos_riesgo >= 1:
        return "medio", "Riesgo Medio"
    return "bajo", "Riesgo Bajo"
