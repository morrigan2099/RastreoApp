import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import folium
import math
import re
from streamlit_folium import st_folium
from folium.plugins import PolyLineTextPath

# ==========================================================
# CONFIGURACIÓN
# ==========================================================
st.set_page_config(page_title="Siguiendo-T", layout="wide")

# ==========================================================
# CONEXIONES
# ==========================================================
try:
    AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]
    AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    AIRTABLE_TABLE_NAME = st.secrets["AIRTABLE_TABLE_NAME"]
    g_creds = dict(st.secrets["google_creds"])
    g_creds["private_key"] = g_creds["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(g_creds, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
except Exception as e:
    st.error(f"❌ Error: {e}")
    st.stop()

# ==========================================================
# FUNCIONES
# ==========================================================
def obtener_url_final(valor):
    if not valor: return None
    if isinstance(valor, list) and len(valor) > 0 and isinstance(valor[0], dict):
        return valor[0].get("url")
    val_str = str(valor).strip()
    if val_str.lower() in ['nan', 'none', '', '[]']: return None
    if val_str.startswith('http'): return val_str
    urls = re.findall(r'(https?://[^\s\)]+)', val_str)
    return urls[0] if urls else None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# PROCESAMIENTO
# ==========================================================
records = table.all()
if not records:
    st.warning("Sin datos.")
    st.stop()

df = pd.DataFrame([r["fields"] for r in records])
df.columns = [c.lower() for c in df.columns]
rename = {c: "Latitud" if "lat" in c else "Longitud" if "lon" in c else "Usuario" if "usu" in c else "Hora" if "hora" in c else "Foto" if ("foto" in c and "etiq" not in c) else c for c in df.columns}
df = df.rename(columns=rename)

df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
df = df.dropna(subset=["Latitud", "Longitud"])
df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
df = df.sort_values("Hora_dt")

if "Foto" in df.columns:
    df["url_limpia"] = df["Foto"].apply(obtener_url_final)
else:
    df["url_limpia"] = None

# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    usuarios_lista = sorted(df["Usuario"].dropna().unique().tolist())
    sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
    
    st.markdown("---")
    tipo_mapa = st.radio("Capa Mapa", ["Calle", "Satélite"], label_visibility="collapsed")
    ver_miniaturas = st.checkbox("📸 Ver Miniaturas en Mapa", value=True)
    
    st.markdown("---")
    # EL BOTÓN MÁGICO
    modo_reporte = st.checkbox("📑 Activar Vista de Impresión (2 Páginas)", value=False)
    
    if st.button("🔄 Actualizar"): st.rerun()

if not sel_usuarios:
    st.stop()

# ==========================================================
# CSS MAESTRO (Print Rules + Page Break)
# ==========================================================
st.markdown(f"""
<style>
/* 1. LIMPIEZA INTERFAZ */
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}}
header[data-testid="stHeader"] {{ background: transparent !important; }}
header[data-testid="stHeader"] button {{ color: var(--text-color) !important; z-index: 9999; }}
[data-testid="stDecoration"] {{ display: none !important; }}
footer {{ display: none !important; }}

/* 2. REGLAS DE IMPRESIÓN */
@media print {{
    @page {{ size: landscape; margin: 0.5cm; }}
    [data-testid="stSidebar"] {{ display: none !important; }}
    header, footer {{ display: none !important; }}
    .stApp {{ margin: 0 !important; }}
    body {{ -webkit-print-color-adjust: exact; background-color: white !important; color: black !important; }}
    
    /* CLASE CLAVE PARA EL CORTE DE HOJA */
    .page-break {{ 
        page-break-before: always !important; 
        break-before: page !important; 
        display: block; 
        height: 0; 
        margin: 0;
    }}
}}

/* 3. TÍTULO */
.title-container {{
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    margin-left: 0px;
    color: var(--text-color);
}}
.title-emoji {{
    font-size: {'80px' if modo_reporte else 'clamp(50px, 14vw, 75px)'};
    margin-right: 15px;
    line-height: 1;
}}
.title-text-block {{ display: flex; flex-direction: column; justify-content: center; }}
.title-main {{
    font-weight: 900;
    font-size: {'48px' if modo_reporte else 'clamp(28px, 8vw, 42px)'};
    line-height: 1.0;
    text-transform: uppercase;
}}
.title-sub {{
    font-weight: 600;
