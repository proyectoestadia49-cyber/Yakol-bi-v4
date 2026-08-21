"""
extractores.py -- Etapa 3: Extraccion de informacion
------------------------------------------------------
Una funcion por tipo de reporte. Cada una recibe la ruta de un PDF YA
CLASIFICADO y regresa un DataFrame con columnas estandarizadas.

Corrige un problema detectado en la version anterior: el extractor de
"Bonos Promotores" no capturaba Bono Vida, Bono GMMI, Bono Beneficios,
Subsidio Renta ni Bono de Crecimiento -- solo Conexion, Desarrollo, IGC y
LIMRA. Este modulo los extrae todos, directamente del PDF, sin recalcular
ningun valor que SMNYL ya haya calculado.
"""

import re
import pdfplumber
import pandas as pd


# ---------------------------------------------------------------------------
# Utilidades comunes de limpieza
# ---------------------------------------------------------------------------

def _limpiar_texto(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).replace("\n", " ")).strip()


def _es_codigo_asesor(s) -> bool:
    return s is not None and bool(re.fullmatch(r"\d{4,6}", str(s).strip()))


def _a_numero(s):
    if s in (None, ""):
        return None
    s = str(s).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _tabla_filas_por_codigo_asesor(ruta_pdf: str) -> list:
    """Extrae todas las filas de tabla cuya primera columna es un codigo
    numerico de asesor (4-6 digitos) -- patron valido para IGC, LIMRA, GMM,
    Conexion/Desarrollo."""
    filas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                for fila in tabla:
                    if fila and _es_codigo_asesor(fila[0]):
                        filas.append([_limpiar_texto(x) for x in fila])
    return filas


def _ajustar_ancho(filas: list, n_columnas: int) -> list:
    return [(f + [""] * n_columnas)[:n_columnas] for f in filas]


# ---------------------------------------------------------------------------
# Extractor: IGC
# ---------------------------------------------------------------------------

def extraer_igc(ruta_pdf: str) -> pd.DataFrame:
    columnas = ["ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso",
                "Prima_PorConservar_Trad", "Prima_Conservada_Trad", "IGC_Trad",
                "Prima_PorConservar_Univ", "Prima_Conservada_Univ", "IGC_Univ",
                "Prima_PorConservar_Total", "Prima_Conservada_Total", "IGC_Calculado",
                "IGC_Indice_Real", "Pct_CargoAuto"]
    filas = _ajustar_ancho(_tabla_filas_por_codigo_asesor(ruta_pdf), len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in columnas:
        if c not in ("ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso"):
            df[c] = df[c].apply(_a_numero)
    return df


# ---------------------------------------------------------------------------
# Extractor: LIMRA
# ---------------------------------------------------------------------------

def extraer_limra(ruta_pdf: str) -> pd.DataFrame:
    columnas = ["ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso",
                "Prima_Cancelada_Trad", "Prima_Emitida_Trad", "LIMRA_Trad",
                "Prima_Cancelada_Univ", "Prima_Emitida_Univ", "LIMRA_Univ",
                "Prima_Cancelada_Total", "Prima_Emitida_Total", "Total_Conservado",
                "LIMRA_Calculado", "LIMRA_Indice_Real", "A_P"]
    filas = _ajustar_ancho(_tabla_filas_por_codigo_asesor(ruta_pdf), len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in columnas:
        if c not in ("ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso"):
            df[c] = df[c].apply(_a_numero)
    return df


# ---------------------------------------------------------------------------
# Extractor: GMM
# ---------------------------------------------------------------------------

def extraer_gmm(ruta_pdf: str) -> pd.DataFrame:
    columnas = ["ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso",
                "Primas_Iniciales_Mes", "Primas_Iniciales_Trimestre",
                "Primas_Iniciales_Mes_AlfaMedicalFlex", "Primas_Iniciales_Trim_AlfaMedicalFlex",
                "Primas_Renovacion_Mes", "Primas_Renovacion_Trimestre",
                "Polizas_Mes", "Polizas_Trimestre",
                "Grupo_Polizas_Iniciales", "Grupo_Concursos_Iniciales",
                "Grupo_Polizas_Renovacion", "Grupo_Concursos_Renovacion"]
    filas = _ajustar_ancho(_tabla_filas_por_codigo_asesor(ruta_pdf), len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in columnas:
        if c not in ("ID_Asesor", "Nombre_Asesor", "Fecha_Ingreso"):
            df[c] = df[c].apply(_a_numero)
    return df


# ---------------------------------------------------------------------------
# Extractor: Actividad
# ---------------------------------------------------------------------------

def extraer_actividad(ruta_pdf: str) -> pd.DataFrame:
    filas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                for fila in tabla:
                    if fila and len(fila) > 1 and _es_codigo_asesor(fila[1]):
                        filas.append([_limpiar_texto(x) for x in fila])
    columnas = ["ID_Promotor", "ID_Asesor", "Nombre_Asesor", "Fecha_Concurso",
                "Polizas_Vida", "Polizas_GMMI", "Produccion_Total_Semestral", "Bono_Por_Asesor"]
    filas = _ajustar_ancho(filas, len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in ["Polizas_Vida", "Polizas_GMMI", "Produccion_Total_Semestral", "Bono_Por_Asesor"]:
        df[c] = df[c].apply(_a_numero)
    return df


# ---------------------------------------------------------------------------
# Extractor: Conexion y Desarrollo (nivel asesor)
# ---------------------------------------------------------------------------

def extraer_conexion_desarrollo(ruta_pdf: str) -> pd.DataFrame:
    filas = _tabla_filas_por_codigo_asesor(ruta_pdf)
    columnas = ["ID_Asesor", "Inicio_Concurso", "Mes_Num", "Polizas_Del_Mes",
                "Cumple_Polizas", "Bono_Del_Mes", "Bono_Adicional", "Bono_A_Pagar"]
    filas = _ajustar_ancho(filas, len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in ["Mes_Num", "Polizas_Del_Mes", "Bono_Del_Mes", "Bono_Adicional", "Bono_A_Pagar"]:
        df[c] = df[c].apply(_a_numero)
    df["Cumple_Polizas"] = df["Cumple_Polizas"].map({"\u2714": True, "\u2715": False}).fillna(False)
    return df


# ---------------------------------------------------------------------------
# Extractor: Traspasos
# ---------------------------------------------------------------------------

def extraer_traspasos(ruta_pdf: str) -> pd.DataFrame:
    filas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                for fila in tabla:
                    rc = [_limpiar_texto(x) for x in fila]
                    if rc and rc[0] and rc[0] not in ("POLIZA", ""):
                        filas.append(rc)
    columnas = ["Poliza", "Recibo", "Producto", "ID_Asesor", "Fecha_Emision",
                "Fecha_Pago", "Prima_Comision", "Comision_Meta", "Comision_Pago",
                "Prima_Meta", "Prima_Pago", "Motivo_Traspaso", "Fecha_Traspaso"]
    filas = _ajustar_ancho(filas, len(columnas))
    df = pd.DataFrame(filas, columns=columnas)
    for c in ["Prima_Comision", "Comision_Meta", "Comision_Pago", "Prima_Meta", "Prima_Pago"]:
        df[c] = df[c].apply(_a_numero)
    return df


# ---------------------------------------------------------------------------
# Extractor: Subsidio a Promotores
# ---------------------------------------------------------------------------

def extraer_subsidio(ruta_pdf: str) -> pd.DataFrame:
    bloques, bloque_actual = [], None
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                if not tabla:
                    continue
                encabezado = tabla[0]
                es_encabezado = encabezado and (encabezado[0] == "" or "AGENTE" in str(encabezado[0]).upper())
                datos = tabla[1:] if es_encabezado else tabla
                datos = [f for f in datos if f and _es_codigo_asesor(str(f[0]))]
                if not datos:
                    continue
                ncols = len(datos[0])
                if bloque_actual is None or (es_encabezado and ncols != bloque_actual["ncols"]):
                    bloque_actual = {"ncols": ncols, "filas": []}
                    bloques.append(bloque_actual)
                elif es_encabezado and ncols == bloque_actual["ncols"]:
                    existentes = {f[0] for f in bloque_actual["filas"]}
                    nuevos = {f[0] for f in datos}
                    if existentes and not (existentes & nuevos):
                        bloque_actual = {"ncols": ncols, "filas": []}
                        bloques.append(bloque_actual)
                bloque_actual["filas"].extend([[_limpiar_texto(x) for x in f] for f in datos])

    frames = []
    for i, b in enumerate(bloques):
        concepto = f"Concepto_{chr(65 + i)}"
        if b["ncols"] == 7:
            columnas = ["ID_Asesor", "Nombre_Asesor", "Inicio_Concurso", "Proactivo",
                        "Polizas_Vida_Semestre", "Polizas_GMM_Semestre", "ID_Promotor"]
        else:
            n_meses = b["ncols"] - 4
            columnas = ["ID_Asesor", "Nombre_Asesor", "Inicio_Concurso", "Total"] + \
                       [f"Mes_{j+1}" for j in range(n_meses)] + ["ID_Promotor"]
        df = pd.DataFrame(_ajustar_ancho(b["filas"], len(columnas)), columns=columnas)
        for c in df.columns:
            if c not in ("ID_Asesor", "Nombre_Asesor", "Inicio_Concurso", "ID_Promotor"):
                df[c] = df[c].apply(_a_numero)
        df["Concepto_Subsidio"] = concepto
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["ID_Asesor", "Nombre_Asesor", "Concepto_Subsidio"])
    return pd.concat(frames, ignore_index=True, sort=False)


# ---------------------------------------------------------------------------
# Extractor: Bonos Promotores -- FUENTE OFICIAL de todos los bonos del
# promotor. Se extraen los 10 conceptos exactamente como aparecen impresos,
# sin recalcular ninguno.
# ---------------------------------------------------------------------------

# Orden fijo en el que estos 10 valores aparecen en el bloque de resumen del
# PDF (validado contra los 5 meses reales de enero a mayo 2026). Si SMNYL
# cambia el layout, la cantidad de valores encontrados dejara de ser 10 y
# la extraccion se marcara como incompleta en vez de asignar mal los datos.
ORDEN_CAMPOS_RESUMEN_BONOS = [
    "Bono_Vida", "LIMRA", "Bono_GMMI", "IGC", "Bono_Beneficios",
    "Subsidio_Renta", "Bono_Conexion", "Bono_Desarrollo", "Bono_Crecimiento", "Bono_Total",
]


def extraer_bonos_promotores(ruta_pdf: str) -> dict:
    """Regresa un diccionario (no un DataFrame) porque este reporte
    describe UN SOLO promotor -- nunca debe generar mas de un renglon.
    Ver transformacion.py para como se integra al Resumen_Bonos."""
    with pdfplumber.open(ruta_pdf) as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages)

    id_promotor = _buscar_texto(texto, r"PROM\s*-\s*(\d+)", default="0000")
    nombre_promotor = _buscar_texto(texto, r"PROM\s*-\s*\d+\s+([A-ZÁÉÍÓÚÑ ]+?)(?:\s+FECHA DE|\n)", default="")

    inicio = texto.find("Bono Vida")
    fin = texto.find("del Mes")
    resultado = {campo: None for campo in ORDEN_CAMPOS_RESUMEN_BONOS}
    extraccion_completa = False

    if inicio != -1 and fin != -1:
        bloque = texto[inicio: fin + len("del Mes")]
        valores = re.findall(r"\d{0,3}(?:,\d{3})*\.\d{2}", bloque)
        if len(valores) == len(ORDEN_CAMPOS_RESUMEN_BONOS):
            for campo, valor in zip(ORDEN_CAMPOS_RESUMEN_BONOS, valores):
                resultado[campo] = _a_numero(valor)
            extraccion_completa = True

    return {
        "ID_Promotor": f"PRM-{id_promotor}",
        "Nombre_Promotor": nombre_promotor,
        **resultado,
        "Bono_Total_Es_Oficial": extraccion_completa,
    }


def _buscar_texto(texto: str, patron: str, default: str = "") -> str:
    m = re.search(patron, texto)
    return m.group(1).strip() if m else default


# ---------------------------------------------------------------------------
# Extractor: Excel mensual de Polizas Pagadas (Vida y GMM) -- NO es un PDF del
# ZIP, es un Excel independiente que Yakol comparte por separado. Fuente
# prioritaria de produccion (polizas PAGADAS, no emitidas) y primaje real.
# ---------------------------------------------------------------------------

def _normalizar_columna(nombre) -> str:
    """Quita acentos/caracteres no-ascii y normaliza espacios, para poder
    comparar nombres de columna aunque el archivo tenga el encoding roto
    (ej. 'P�lizas' en vez de 'Polizas') -- se compara contra objetivos
    que ya pasaron por la misma normalizacion."""
    s = re.sub(r"\s+", " ", str(nombre).strip().lower())
    return "".join(c for c in s if ord(c) < 128)


def _detectar_fila_encabezado(df_crudo: pd.DataFrame) -> int:
    """Algunas hojas (ej. VIDA) traen una fila de titulo extra antes del
    encabezado real -- se busca la primera fila que contenga una celda que
    normalice a 'asesor', en vez de asumir que el encabezado es la fila 0."""
    for i in range(min(5, len(df_crudo))):
        valores = [_normalizar_columna(v) for v in df_crudo.iloc[i].tolist()]
        if "asesor" in valores:
            return i
    return 0


_COLUMNAS_OBJETIVO_POLIZAS_PAGADAS = {
    "asesor": "ID_Asesor", "nombre asesor": "Nombre_Asesor", "plizas": "Polizas_Pagadas",
    "recibo inicial": "Recibo_Inicial", "recibo ordinario": "Recibo_Ordinario",
    "total prima inicial": "Prima_Pagada_Total",
}


def extraer_polizas_pagadas(ruta_excel: str) -> pd.DataFrame:
    """Lee las hojas 'VIDA' y 'GMM' del Excel mensual de Polizas Pagadas y
    regresa un solo DataFrame combinado con columna Producto ('Vida'/'GMM').
    Fecha de Conexion, Grupo y Sucursal se leen implicitamente pero se
    descartan -- no se necesitan para ningun calculo del sistema."""
    columnas_finales = ["ID_Asesor", "Nombre_Asesor", "Polizas_Pagadas",
                         "Recibo_Inicial", "Recibo_Ordinario", "Prima_Pagada_Total"]
    partes = []
    for nombre_hoja, producto in (("VIDA", "Vida"), ("GMM", "GMM")):
        try:
            crudo = pd.read_excel(ruta_excel, sheet_name=nombre_hoja, header=None)
        except ValueError:
            continue  # la hoja no existe en este archivo
        fila_encabezado = _detectar_fila_encabezado(crudo)
        df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja, header=fila_encabezado)

        mapeo = {col: _COLUMNAS_OBJETIVO_POLIZAS_PAGADAS[_normalizar_columna(col)]
                 for col in df.columns if _normalizar_columna(col) in _COLUMNAS_OBJETIVO_POLIZAS_PAGADAS}
        df = df.rename(columns=mapeo)
        for c in columnas_finales:
            if c not in df.columns:
                df[c] = None
        df = df[columnas_finales].copy()

        df = df[df["ID_Asesor"].notna()]
        df["ID_Asesor"] = df["ID_Asesor"].apply(
            lambda v: str(int(v)) if isinstance(v, (int, float)) and not pd.isna(v) else str(v).strip())
        df = df[df["ID_Asesor"].str.fullmatch(r"\d{4,6}")]
        for c in ["Polizas_Pagadas", "Recibo_Inicial", "Recibo_Ordinario", "Prima_Pagada_Total"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["Producto"] = producto
        partes.append(df)

    if not partes:
        return pd.DataFrame(columns=columnas_finales + ["Producto"])
    return pd.concat(partes, ignore_index=True)


# ---------------------------------------------------------------------------
# Registro central: tipo de reporte -> funcion extractora
# ---------------------------------------------------------------------------

EXTRACTORES = {
    "IGC": extraer_igc, "LIMRA": extraer_limra, "GMM": extraer_gmm,
    "Actividad": extraer_actividad, "ConexionDesarrollo": extraer_conexion_desarrollo,
    "Traspasos": extraer_traspasos, "Subsidio": extraer_subsidio,
    "BonosAsesores": extraer_gmm,  # respaldo generico si no calza ninguna firma especifica
}
