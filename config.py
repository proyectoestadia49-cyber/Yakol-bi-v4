"""
config.py -- Configuracion central del proyecto YAKOL BI (Excel Maestro)
--------------------------------------------------------------------------
Unico lugar donde viven las "reglas fijas" del sistema: como se identifica
cada tipo de reporte, que columnas debe tener cada tabla del Excel Maestro,
y los umbrales normativos de IGC/LIMRA. Ningun otro modulo debe repetir
estas constantes -- todos las importan desde aqui.
"""

MESES_ES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
            "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

# Cuentas tecnicas de SMNYL que aparecen en los reportes de asesores pero
# NO son asesores reales (ej. la cuenta "SEGUROS MONTERREY NEW YORK LIFE"
# con clave 64939, identificada en sesiones previas de este proyecto).
# Se excluyen de todo analisis de cumplimiento y segmentacion.
IDS_ASESOR_EXCLUIDOS = ["64939"]

UMBRAL_IGC = 90.25  # Valor minimo oficial de referencia (antes 86.75 -- corregido)
UMBRAL_LIMRA = 86.00  # Valor minimo oficial de referencia (antes 85.5 -- corregido)
RAMPA_IGC_MESES = 15
RAMPA_LIMRA_MESES = 24

# ---------------------------------------------------------------------------
# Firmas de clasificacion: cada tipo de reporte se identifica por texto que
# SIEMPRE aparece en su primera pagina, nunca por el nombre del archivo
# (SMNYL no nombra los PDF de forma consistente entre meses).
# ---------------------------------------------------------------------------
FIRMAS_REPORTES = [
    {"tipo": "BonosPromotores", "debe_contener": ["REPORTE DE BONOS PROMOTORES"], "no_debe_contener": []},
    {"tipo": "Actividad", "debe_contener": ["ACTIVIDAD"], "no_debe_contener": ["REPORTE DE BONOS"]},
    {"tipo": "Subsidio", "debe_contener": ["SUBSIDIO A PROMOTORES"], "no_debe_contener": []},
    {"tipo": "ConexionDesarrollo", "debe_contener": ["DETALLE BONO DE CONEXION Y DESARROLLO"], "no_debe_contener": []},
    {"tipo": "Traspasos", "debe_contener": ["DETALLE TRASPASOS"], "no_debe_contener": []},
    {"tipo": "LIMRA", "debe_contener": ["REPORTE DE BONOS ASESORES", "LIMRA"], "no_debe_contener": []},
    {"tipo": "LIMRA", "debe_contener": ["LIMBRA"], "no_debe_contener": []},
    {"tipo": "GMM", "debe_contener": ["REPORTE DE BONOS ASESORES", "PRIMAS INICIALES"], "no_debe_contener": []},
    {"tipo": "IGC", "debe_contener": ["REPORTE DE BONOS ASESORES", "IGC"], "no_debe_contener": ["LIMRA", "LIMBRA", "PRIMAS INICIALES"]},
    {"tipo": "BonosAsesores", "debe_contener": ["REPORTE DE BONOS ASESORES"], "no_debe_contener": []},
]

# Reportes que se esperan en cada ZIP mensual (para el Log_Procesamiento)
TIPOS_REPORTE_ESPERADOS = [
    "BonosPromotores", "IGC", "LIMRA", "GMM", "Actividad",
    "ConexionDesarrollo", "Traspasos", "Subsidio",
]

# ---------------------------------------------------------------------------
# Esquema del Excel Maestro: que hoja contiene que columnas.
# Definir esto en un solo lugar evita que dos modulos distintos escriban
# columnas con nombres ligeramente distintos para el mismo dato.
# ---------------------------------------------------------------------------
COLUMNAS_DIM_ASESOR = ["ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso"]
COLUMNAS_DIM_PROMOTOR = ["ID_Promotor", "Nombre_Promotor"]
COLUMNAS_DIM_PERIODO = ["ID_Periodo", "Anio", "Mes", "Nombre_Mes"]

COLUMNAS_FACT_IGC = ["ID_Asesor", "ID_Periodo", "IGC_Indice_Real"]
COLUMNAS_FACT_LIMRA = ["ID_Asesor", "ID_Periodo", "LIMRA_Indice_Real"]

COLUMNAS_HISTORICO_ACTIVIDAD = [
    "ID_Periodo", "ID_Promotor", "ID_Asesor", "Nombre_Asesor", "Fecha_Concurso",
    "Polizas_Vida", "Polizas_GMMI", "Produccion_Total_Semestral", "Bono_Por_Asesor",
]

COLUMNAS_HISTORICO_GMM = [
    "ID_Periodo", "ID_Asesor", "Primas_Iniciales_Mes", "Primas_Renovacion_Mes", "Polizas_Mes",
]

COLUMNAS_HISTORICO_TRASPASOS = [
    "ID_Periodo", "ID_Registro", "ID_Asesor", "Poliza", "Producto",
    "Prima_Pago", "Comision_Pago", "Motivo_Traspaso", "Fecha_Traspaso",
]

COLUMNAS_HISTORICO_CONEXION_DESARROLLO = [
    "ID_Periodo", "ID_Asesor", "Mes_Num", "Polizas_Del_Mes", "Cumple_Polizas", "Bono_A_Pagar",
]

# Excel mensual de Polizas Pagadas (Vida y GMM) -- fuente PRIORITARIA de produccion,
# distinta del reporte "Actividad" del ZIP: Actividad mide polizas EMITIDAS (Cuaderno de
# Concursos), este Excel mide polizas PAGADAS con su primaje real. Cuando esta
# disponible para un asesor/periodo, tiene prioridad sobre la aproximacion anterior en
# todo el sistema (Indice de Salud, Destacados, Riesgo, Real vs Plan) -- ver
# calcular_indice_salud_negocio() y calcular_real_vs_plan() en analitica_avanzada.py.
COLUMNAS_HISTORICO_POLIZAS_PAGADAS = [
    "ID_Periodo", "ID_Asesor", "Nombre_Asesor", "Producto",
    "Polizas_Pagadas", "Recibo_Inicial", "Recibo_Ordinario", "Prima_Pagada_Total",
]

# ---------------------------------------------------------------------------
# Modulos analiticos -- constantes de negocio (no relacionadas con bonos
# oficiales, que nunca se recalculan)
# ---------------------------------------------------------------------------

META_ANUAL_POLIZAS_VIDA = 300
META_ANUAL_ASESORES_NUEVOS = 18

SUELDO_SHARON_DEFAULT = 12000.0  # Confirmado por Gerardo: el presupuesto trae $10,800 por error
PCT_SHARON_RECLUTAMIENTO_DEFAULT = 40.0

# ---------------------------------------------------------------------------
# Presupuesto real de Yakol (35 conceptos, fuente: documento de presupuesto
# proporcionado por la promotoria). Reemplaza por completo el supuesto
# anterior de $60,000/mes de costos fijos.
#
# "Nomina Sharon" y "Nomina Carmen" se EXCLUYEN de este listado a proposito:
# Sharon ya se calcula por separado con SUELDO_SHARON_DEFAULT x
# PCT_SHARON_RECLUTAMIENTO_DEFAULT (evita contarla dos veces), y Carmen fue
# confirmada por Gerardo como administrativa general, no atribuible a
# reclutamiento (se excluye del todo del costeo de reclutamiento).
# ---------------------------------------------------------------------------

# (concepto, categoria, tipo, periodicidad, monto)
PRESUPUESTO_YAKOL = [
    ("Renta de oficinas", "Instalaciones y Servicios", "Fijo", "Mensual", 16397.00),
    ("Mantenimiento de oficina", "Instalaciones y Servicios", "Fijo", "Mensual", 3650.00),
    ("Luz", "Instalaciones y Servicios", "Variable", "Bimestral", 2600.00),
    ("Limpieza de oficina", "Instalaciones y Servicios", "Fijo", "Mensual", 1800.00),
    ("Internet", "Instalaciones y Servicios", "Fijo", "Mensual", 1160.00),
    ("Celulares", "Instalaciones y Servicios", "Fijo", "Mensual", 2385.00),
    ("IMSS", "Personal, Impuestos y Cumplimiento", "Fijo", "Bimestral", 14200.00),
    ("ISN", "Personal, Impuestos y Cumplimiento", "Variable", "Mensual", 700.00),
    ("SAT - IVA", "Personal, Impuestos y Cumplimiento", "Variable", "Mensual", 8000.00),
    ("SAT - Retenciones", "Personal, Impuestos y Cumplimiento", "Variable", "Mensual", 2500.00),
    ("Servicios contables", "Personal, Impuestos y Cumplimiento", "Fijo", "Mensual", 5900.00),
    ("Licencia de funcionamiento", "Personal, Impuestos y Cumplimiento", "Fijo", "Anual", 1200.00),
    ("Gasolina", "Operacion", "Variable", "Mensual", 8000.00),
    ("Comidas", "Operacion", "Variable", "Mensual", 2000.00),
    ("Material de oficina", "Operacion", "Variable", "Semestral", 9000.00),
    ("Material para cafe", "Operacion", "Variable", "Mensual", 1000.00),
    ("Material de limpieza - consumo mensual", "Operacion", "Variable", "Mensual", 500.00),
    ("Material de limpieza - reposicion", "Operacion", "Variable", "Semestral", 1200.00),
    ("Aguinaldo Carmen", "Prestaciones y Cierre de Ano", "Fijo", "Anual", 6500.00),
    ("Aguinaldo Sharon", "Prestaciones y Cierre de Ano", "Fijo", "Anual", 6000.00),
    ("Fiesta de fin de ano", "Prestaciones y Cierre de Ano", "Variable", "Anual", 10000.00),
    ("Paquete Office", "Tecnologia y Suscripciones", "Fijo", "Anual", 2229.00),
    ("Google Workspace - David", "Tecnologia y Suscripciones", "Fijo", "Mensual", 280.00),
    ("Captions - David", "Tecnologia y Suscripciones", "Fijo", "Mensual", 499.00),
    ("ChatGPT - David", "Tecnologia y Suscripciones", "Fijo", "Mensual", 399.00),
    ("GoDaddy / Correo Carmen", "Tecnologia y Suscripciones", "Fijo", "Mensual", 49.00),
    ("CapCut", "Tecnologia y Suscripciones", "Fijo", "Mensual", 165.00),
    ("Notion", "Tecnologia y Suscripciones", "Fijo", "Mensual", 973.11),
    ("iCloud Familiar - David", "Tecnologia y Suscripciones", "Fijo", "Mensual", 499.00),
    ("Club Maple", "Tecnologia y Suscripciones", "Fijo", "Mensual", 549.00),
    ("ChatGPT - Yakol", "Tecnologia y Suscripciones", "Fijo", "Mensual", 399.00),
    ("Dominio GoDaddy - Yakol", "Tecnologia y Suscripciones", "Fijo", "Anual", 400.00),
    ("Drive - Yakol", "Tecnologia y Suscripciones", "Fijo", "Anual", 170.00),
]

_FACTOR_MENSUALIZACION = {"Mensual": 1, "Bimestral": 1 / 2, "Semestral": 1 / 6, "Anual": 1 / 12}


def calcular_presupuesto_mensualizado() -> float:
    """Suma el presupuesto completo, ya mensualizado (ej. un gasto bimestral
    de $2,600 se cuenta como $1,300/mes). No incluye Sharon ni Carmen -- ver
    nota arriba."""
    return round(sum(monto * _FACTOR_MENSUALIZACION[periodicidad]
                      for _, _, _, periodicidad, monto in PRESUPUESTO_YAKOL), 2)


# Numero de funciones centrales de la promotoria, usado para prorratear
# automaticamente que fraccion del presupuesto general (renta, luz,
# impuestos, tecnologia, etc.) es atribuible a reclutamiento. Supuesto
# metodologico explicito -- el director no ha confirmado un porcentaje
# exacto. Las 5 funciones consideradas: reclutamiento, servicio a cartera
# existente, cumplimiento normativo, gestion de siniestros GMM, y
# administracion general.
NUMERO_FUNCIONES_PROMOTORIA = 5

# ---------------------------------------------------------------------------
# Indice de Salud del Negocio -- reemplaza la segmentacion por KMeans.
# Fuente: documento "Parametros del Asesor y Presupuesto" proporcionado por
# la promotoria. Metodologia determinista, no estadistica: cada asesor se
# clasifica de forma reproducible mes con mes, no de forma relativa al resto
# del grupo de ese periodo (a diferencia del KMeans anterior).
# ---------------------------------------------------------------------------

# Pesos de cada variable en el Indice de Salud del Negocio (deben sumar 100)
PESOS_INDICE_SALUD = {
    "Polizas_Vida": 25, "Prima_Vida": 25, "Polizas_GMM": 10,
    "Prima_GMM": 10, "LIMRA": 15, "IGC": 15,
}

# Puntaje segun el nivel alcanzado en cada variable
PUNTAJE_POR_NIVEL = {
    "Extraordinario": 100, "Bueno": 85, "Promedio": 70,
    "Proactivo": 55, "Riesgo Medio": 35, "Riesgo Alto": 0,
}

# Bandas de clasificacion final segun el Indice de Salud del Negocio (0-100)
BANDAS_LECTURA_MENSUAL = [
    (90, 100.0001, "Negocio extraordinario"),
    (80, 90, "Alto desempeno"),
    (70, 80, "Negocio saludable"),
    (55, 70, "Negocio en desarrollo"),
    (35, 55, "Riesgo medio"),
    (0, 35, "Riesgo alto"),
]

# ---------------------------------------------------------------------------
# Asesores Destacados -- contraparte del analisis de riesgo. Reutiliza el
# mismo Indice de Salud del Negocio (nunca se inventa un indicador nuevo
# desde cero) y agrega el aporte al bono por actividad (Bono_Por_Asesor,
# columna real de Historico_Actividad, distinta del Bono_Total oficial del
# promotor -- nunca se confunde ni se suma contra ese dato oficial).
# ---------------------------------------------------------------------------

# Piso de calificacion: igual al piso de la banda "Alto desempeno" ya
# definida en BANDAS_LECTURA_MENSUAL -- no se inventa un corte nuevo. Se
# exige que el asesor lo haya alcanzado en AL MENOS UN mes de su historico
# (no en el promedio) -- validado contra los 7 meses reales del proyecto:
# exigirlo en el promedio dejaba la seccion vacia casi todos los meses,
# porque el desempeno mensual es volatil incluso en los mejores asesores.
# El ranking (Indice de Desempeno Destacado) si sigue premiando la
# consistencia sobre todo el historico -- esto solo afecta quien califica.
UMBRAL_INDICE_SALUD_DESTACADO = 80

# Antiguedad minima (en meses) para calificar como destacado -- evita que un
# asesor nuevo con un solo mes excelente entre por poca base de comparacion.
MESES_ANTIGUEDAD_MINIMOS_DESTACADO = 3

# Pesos del Indice de Desempeno Destacado (deben sumar 100). Promedio_Salud
# reutiliza el Indice de Salud del Negocio ya calculado; Consistencia premia
# sostener banda alta varios periodos, no solo un mes suelto; Aporte_Bono
# usa Bono_Por_Asesor normalizado contra el maximo del grupo evaluado.
PESOS_INDICE_DESTACADO = {"Promedio_Salud": 60, "Consistencia": 25, "Aporte_Bono": 15}

# Piso fijo de asesores mostrados en el ranking. El tope real aplicado en
# codigo es max(TOP_DESTACADOS_MINIMO, round(10% de asesores evaluados)),
# para que equipos grandes muestren mas de 10 sin fijar un numero arbitrario.
TOP_DESTACADOS_MINIMO = 10

CANALES_RECLUTAMIENTO = [
    "OCC", "Facebook / Redes Sociales", "Instagram", "TikTok", "LinkedIn",
    "Pagina Web", "Google Business", "WhatsApp (grupos)", "Oficinas",
    "Programa Cazatalentos", "RDA", "Mercado Natural", "Networking",
    "Centro de Influencia", "Club de Lectura / Crecimiento", "Comunidad de Networking",
]

# Conceptos oficiales del resumen de "Reporte de Bonos Promotores" -- estos
# son los UNICOS campos que representan bonos del promotor; nunca se generan
# renglones adicionales por asesor para estos conceptos.
COLUMNAS_RESUMEN_BONOS = [
    "ID_Periodo", "ID_Promotor", "IGC", "LIMRA",
    "Bono_Vida", "Bono_GMMI", "Bono_Beneficios", "Subsidio_Renta",
    "Bono_Conexion", "Bono_Desarrollo", "Bono_Crecimiento", "Bono_Total",
    "Bono_Total_Es_Oficial",
]
