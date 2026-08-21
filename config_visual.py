"""
config_visual.py -- Identidad visual corporativa del Dashboard
--------------------------------------------------------------------
Centraliza colores y estilos para que toda la app (CSS + graficas Plotly)
use exactamente la misma paleta, sin repetir codigos de color en cada
archivo.
"""

COLOR_PRIMARIO = "#0B2A4A"      # Azul marino Yakol -- encabezados, texto principal
COLOR_SECUNDARIO = "#1F5C9E"    # Azul medio -- botones, acentos
COLOR_ACENTO = "#2E86AB"        # Azul-verde -- series secundarias en graficas
COLOR_FONDO = "#F4F7FB"         # Gris muy claro -- fondo general
COLOR_TARJETA = "#FFFFFF"       # Fondo de tarjetas

COLOR_EXITO = "#1E8E5A"         # Verde -- semaforo bajo riesgo / cumple
COLOR_ADVERTENCIA = "#D68A1F"   # Ambar -- semaforo riesgo medio
COLOR_PELIGRO = "#C0392B"       # Rojo -- semaforo alto riesgo / incumple
COLOR_NEUTRO = "#8A94A6"        # Gris -- sin dato / neutro
COLOR_DESARROLLO = "#C9A961"    # Dorado suave -- distinto del ambar, para "Negocio en desarrollo"

PALETA_SEGMENTOS = {
    "Negocio extraordinario": COLOR_EXITO,
    "Alto desempeno": COLOR_EXITO,
    "Negocio saludable": COLOR_ACENTO,
    "Negocio en desarrollo": COLOR_DESARROLLO,
    "Riesgo medio": COLOR_ADVERTENCIA,
    "Riesgo alto": COLOR_PELIGRO,
    "Datos insuficientes": COLOR_NEUTRO,
    "Datos insuficientes para segmentar": COLOR_NEUTRO,
}

FUENTE = "Segoe UI, -apple-system, sans-serif"
PLANTILLA_PLOTLY = "plotly_white"

CSS_CORPORATIVO = f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO}; font-family: {FUENTE}; }}

    #MainMenu, footer, header {{ visibility: hidden; }}

    .yakol-topbar {{
        display: flex; align-items: center; gap: 18px;
        background: linear-gradient(90deg, {COLOR_PRIMARIO} 0%, #123A63 100%);
        padding: 18px 32px; border-radius: 12px; margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(11,42,74,0.25);
    }}
    .yakol-topbar img {{ height: 54px; border-radius: 6px; }}
    .yakol-topbar h1 {{ color: white; margin: 0; font-size: 22px; font-weight: 600; }}
    .yakol-topbar p {{ color: #C9D9EA; margin: 0; font-size: 13px; }}

    .kpi-card {{
        background: {COLOR_TARJETA}; border-radius: 14px; padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(11,42,74,0.08); border-left: 5px solid {COLOR_SECUNDARIO};
        height: 100%;
    }}
    .kpi-card .kpi-label {{
        font-size: 12px; color: {COLOR_NEUTRO}; text-transform: uppercase;
        letter-spacing: 0.06em; font-weight: 600; margin-bottom: 6px;
    }}
    .kpi-card .kpi-value {{ font-size: 30px; font-weight: 700; color: {COLOR_PRIMARIO}; line-height: 1.1; }}
    .kpi-card .kpi-delta {{ font-size: 12px; margin-top: 4px; font-weight: 600; }}
    .kpi-card.exito {{ border-left-color: {COLOR_EXITO}; }}
    .kpi-card.exito .kpi-value {{ color: {COLOR_EXITO}; }}
    .kpi-card.advertencia {{ border-left-color: {COLOR_ADVERTENCIA}; }}
    .kpi-card.advertencia .kpi-value {{ color: {COLOR_ADVERTENCIA}; }}
    .kpi-card.peligro {{ border-left-color: {COLOR_PELIGRO}; }}
    .kpi-card.peligro .kpi-value {{ color: {COLOR_PELIGRO}; }}

    .seccion-titulo {{
        color: {COLOR_PRIMARIO}; font-size: 16px; font-weight: 700;
        margin: 22px 0 10px 0; padding-bottom: 6px; border-bottom: 2px solid #E2E8F0;
    }}

    .semaforo-badge {{
        display: inline-block; padding: 6px 16px; border-radius: 20px;
        font-weight: 700; font-size: 13px; color: white;
    }}
    .semaforo-bajo {{ background-color: {COLOR_EXITO}; }}
    .semaforo-medio {{ background-color: {COLOR_ADVERTENCIA}; }}
    .semaforo-alto {{ background-color: {COLOR_PELIGRO}; }}

    .hallazgo-card {{
        background: {COLOR_TARJETA}; border-radius: 10px; padding: 14px 18px;
        margin-bottom: 10px; box-shadow: 0 1px 6px rgba(11,42,74,0.06);
        border-left: 4px solid {COLOR_SECUNDARIO};
    }}
    .hallazgo-card.riesgo {{ border-left-color: {COLOR_PELIGRO}; }}
    .hallazgo-card.oportunidad {{ border-left-color: {COLOR_EXITO}; }}
    .hallazgo-card.recomendacion {{ border-left-color: {COLOR_ADVERTENCIA}; }}
    .hallazgo-titulo {{ font-weight: 700; color: {COLOR_PRIMARIO}; font-size: 13.5px; margin-bottom: 3px; }}
    .hallazgo-texto {{ font-size: 13px; color: #333; line-height: 1.5; }}
    .hallazgo-seccion {{ font-size: 13px; color: #333; line-height: 1.55; margin-top: 4px; }}
    .hallazgo-seccion b {{ color: {COLOR_PRIMARIO}; }}

    .scroll-container {{
        max-height: 480px; overflow-y: auto; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 4px 14px; background-color: white; margin-bottom: 20px;
    }}
    .riesgo-item {{ border-bottom: 1px solid #EDEFF3; padding: 12px 0; }}
    .riesgo-item:last-child {{ border-bottom: none; }}
    .riesgo-item-titulo {{ font-weight: 700; color: {COLOR_PRIMARIO}; font-size: 13.5px; margin-bottom: 4px; }}
    .riesgo-item-linea {{ font-size: 12.5px; color: #333; line-height: 1.5; margin-bottom: 2px; }}
    .riesgo-badge {{
        display: inline-block; font-size: 10.5px; font-weight: 700; padding: 2px 9px;
        border-radius: 10px; margin-left: 8px; color: white; vertical-align: middle;
    }}
    .riesgo-badge.riesgo-alto {{ background-color: {COLOR_PELIGRO}; }}
    .riesgo-badge.riesgo-medio {{ background-color: {COLOR_ADVERTENCIA}; }}
    .riesgo-badge.riesgo-bajo {{ background-color: {COLOR_NEUTRO}; }}

    .destacado-item {{ border-bottom: 1px solid #EDEFF3; padding: 12px 0; }}
    .destacado-item:last-child {{ border-bottom: none; }}
    .destacado-item-titulo {{ font-weight: 700; color: {COLOR_PRIMARIO}; font-size: 13.5px; margin-bottom: 4px; }}
    .destacado-item-linea {{ font-size: 12.5px; color: #333; line-height: 1.5; margin-bottom: 2px; }}
    .destacado-badge {{
        display: inline-block; font-size: 10.5px; font-weight: 700; padding: 2px 9px;
        border-radius: 10px; margin-left: 8px; color: white; vertical-align: middle;
        background-color: {COLOR_EXITO};
    }}

    .interpretacion-box {{
        background-color: #F4F7FB; border: 1px solid #E2E8F0; border-left: 4px solid {COLOR_SECUNDARIO};
        border-radius: 6px; padding: 12px 16px; margin: 6px 0 22px 0;
        font-size: 13px; color: #333; line-height: 1.55;
    }}
    .interpretacion-box b {{ color: {COLOR_PRIMARIO}; font-size: 12px; letter-spacing: 0.4px; }}

    div.stButton > button {{
        background-color: {COLOR_SECUNDARIO}; color: white; font-weight: 600;
        border-radius: 8px; border: none; padding: 0.6em 1.6em;
    }}
    div.stButton > button:hover {{ background-color: {COLOR_PRIMARIO}; color: white; }}

    div[data-testid="stMetricValue"] {{ color: {COLOR_PRIMARIO}; }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: white; border-radius: 8px 8px 0 0; padding: 10px 20px;
        font-weight: 600; color: {COLOR_NEUTRO};
    }}
    .stTabs [aria-selected="true"] {{ background-color: {COLOR_PRIMARIO}; color: white; }}
</style>
"""
