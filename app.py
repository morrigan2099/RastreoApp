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
    modo_reporte = st.checkbox("📑 Activar Vista de Impresión (2 Páginas)", value=False)
    
    if st.button("🔄 Actualizar"): st.rerun()

if not sel_usuarios:
    st.stop()

# ==========================================================
# CSS BLINDADO
# ==========================================================
# 1. Estilos Estáticos
css_estatico = """
<style>
.block-container {
    padding: 1rem !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
header[data-testid="stHeader"] button { color: var(--text-color) !important; z-index: 9999; }
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }

@media print {
    @page { size: landscape; margin: 0.5cm; }
    [data-testid="stSidebar"] { display: none !important; }
    header, footer { display: none !important; }
    .stApp { margin: 0 !important; }
    body { -webkit-print-color-adjust: exact; background-color: white !important; color: black !important; }
    .page-break { page-break-before: always !important; break-before: page !important; display: block; height: 0; margin: 0; }
}

/* TÍTULO */
.title-container {
    display: flex; align-items: center; margin-bottom: 10px; margin-left: 0px; color: var(--text-color); padding: 10px; overflow: visible;
}
.title-emoji { margin-right: 20px; line-height: 1.2; padding-bottom: 5px; }
.title-text-block { display: flex; flex-direction: column; justify-content: center; }
.title-main { font-weight: 900; line-height: 1.1; text-transform: uppercase; }
.title-sub { font-weight: 600; line-height: 1.2; opacity: 0.9; }

/* TABLA PERSONALIZADA */
.custom-stats-table { width: 100%; border-collapse: collapse; font-family: sans-serif; margin-top: 5px; }
.custom-stats-table th { background-color: #000; color: #fff; padding: 6px 10px; text-align: left; font-size: 14px; border: 2px solid #000; }
.custom-stats-table td { border: 2px solid #000; padding: 6px 10px; font-size: 16px; font-weight: bold; color: #000; }
.color-dot { display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 8px; border: 1px solid #000; vertical-align: middle; }

/* GALERÍA */
.gallery-container { display: flex; flex-wrap: wrap; margin: 0 -4px; justify-content: flex-start; }
.gallery-item { box-sizing: border-box; padding: 4px; }
@media (max-width: 768px) { .gallery-item { width: 50% !important; } }

.photo-card { border: 1px solid #ddd; border-radius: 6px; background-color: #f0f2f6; overflow: hidden; height: 210px; display: flex; flex-direction: column; }
.photo-card img { width: 100%; height: 185px; object-fit: contain; background-color: #ababb3; }
.photo-caption { height: 25px; background: #fff; color: #000; font-size: 10px; font-weight: 600; display: flex; align-items: center; justify-content: center; border-top: 1px solid #ccc; }
</style>
"""

# 2. Estilos Dinámicos
size_emoji = '90px' if modo_reporte else 'clamp(50px, 14vw, 75px)'
size_main = '50px' if modo_reporte else 'clamp(28px, 8vw, 42px)'
size_sub = '28px' if modo_reporte else 'clamp(16px, 5vw, 24px)'
width_item = '16.66%' if modo_reporte else '25%'

css_dinamico = f"""
<style>
.title-emoji {{ font-size: {size_emoji}; }}
.title-main {{ font-size: {size_main}; }}
.title-sub {{ font-size: {size_sub}; }}
.gallery-item {{ width: {width_item}; }}
</style>
"""
st.markdown(css_estatico + css_dinamico, unsafe_allow_html=True)

# ==========================================================
# PRE-CÁLCULO DE DATOS (TABLA HTML Y COORDENADAS)
# ==========================================================
df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']

stats_rows_html = []
all_coords = []

# Bucle para generar datos de la tabla y coordenadas del mapa
for i, nombre in enumerate(sel_usuarios):
    color = colores[i % len(colores)]
    u_data = df_f[df_f["Usuario"] == nombre]
    
    # Distancia
    dist_u = 0.0
    coords = u_data[["Latitud", "Longitud"]].values.tolist()
    all_coords.extend(coords)
    if len(coords) > 1:
        for k in range(len(coords)-1):
            dist_u += calcular_distancia(coords[k][0], coords[k][1], coords[k+1][0], coords[k+1][1])
            
    # Fotos
    fotos_count = u_data['url_limpia'].notna().sum()
    dist_fmt = f"{dist_u:.2f} km"
    
    # CREACIÓN DE FILA HTML (EN UNA SOLA LÍNEA PARA NO ROMPER MARKDOWN)
    row_html = f'<tr><td><span class="color-dot" style="background-color: {color};"></span>{nombre}</td><td>{fotos_count}</td><td>{dist_fmt}</td></tr>'
    stats_rows_html.append(row_html)

# Unimos las filas
rows_str = "".join(stats_rows_html)

# Construimos la Tabla Completa
html_tabla = f"""
<table class="custom-stats-table">
    <thead>
        <tr><th>Repartidor</th><th>Fotos</th><th>Distancia</th></tr>
    </thead>
    <tbody>{rows_str}</tbody>
</table>
"""

# Título HTML
html_titulo = """
<div class="title-container">
    <div class="title-emoji">🏃🏽‍♂️</div>
    <div class="title-text-block">
        <div class="title-main">Siguiendo-T</div>
        <div class="title-sub">Monitor de Reparto</div>
    </div>
</div>
"""

# ==========================================================
# RENDERIZADO VISUAL
# ==========================================================

# 1. PÁGINA 1: Encabezado y Mapa
if modo_reporte:
    col1, col2 = st.columns([1.5, 1])
    with col1:
        st.markdown(html_titulo, unsafe_allow_html=True)
    with col2:
        st.markdown(html_tabla, unsafe_allow_html=True)
else:
    st.markdown(html_titulo, unsafe_allow_html=True)

# MAPA
alto_mapa = 700 if modo_reporte else 250
m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)

if tipo_mapa == "Satélite":
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

for i, nombre in enumerate(sel_usuarios):
    color = colores[i % len(colores)]
    u_data = df_f[df_f["Usuario"] == nombre].reset_index(drop=True)
    
    if not u_data.empty:
        coords = u_data[["Latitud", "Longitud"]].values.tolist()
        if len(coords) > 1:
            linea = folium.PolyLine(coords, color=color, weight=4, opacity=0.8).add_to(m)
            # Flechas
            PolyLineTextPath(linea, '                    ▶                    ', repeat=True, offset=20, attributes={'fill': color, 'font-size': '12'}).add_to(m)

        r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
        off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
        folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}").add_to(m)
        folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}").add_to(m)
        
        if ver_miniaturas:
            for j, row in u_data.iterrows():
                if row['url_limpia']:
                    popup_html = f'<img src="{row["url_limpia"]}" style="max-width:220px; max-height:220px; object-fit:contain; border-radius:4px;">'
                    folium.Marker([row["Latitud"], row["Longitud"]],
                        icon=folium.DivIcon(html=f'<div style="width:30px; height:30px; border:2px solid {color}; background:white; border-radius:4px; overflow:hidden;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                        popup=folium.Popup(popup_html, max_width=230)).add_to(m)

if all_coords:
    m.fit_bounds(all_coords)

st_folium(m, width="100%", height=alto_mapa, returned_objects=[])

# ESTADÍSTICAS (Si es modo normal, van abajo)
if not modo_reporte:
    st.markdown("### 📊 Estadísticas")
    st.markdown(html_tabla, unsafe_allow_html=True)

# CORTE DE PÁGINA
if modo_reporte:
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)

# 2. PÁGINA 2: Galería
titulo_galeria = "**📸 Evidencias Fotográficas**" if modo_reporte else "### 📸 Evidencias"
st.markdown(titulo_galeria)

df_gal = df_f[df_f['url_limpia'].notna()]
if not df_gal.empty:
    html_parts = ['<div class="gallery-container">']
    for _, row in df_gal.iterrows():
        url = row['url_limpia']
        user = str(row['Usuario']).split()[0].replace("<","").replace(">","")
        hora = str(row['Hora'])[:5]
        # HTML en una línea
        html_parts.append(f'<div class="gallery-item"><a href="{url}" target="_blank" style="text-decoration:none;"><div class="photo-card"><img src="{url}" loading="lazy"><div class="photo-caption">{user} {hora}</div></div></a></div>')
    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)
else:
    st.info("Sin evidencias.")

if not modo_reporte:
    st.markdown("---")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
