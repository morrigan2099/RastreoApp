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
# CONEXIONES Y DATOS
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
# PROCESAMIENTO DE DATOS (COMÚN PARA AMBAS VISTAS)
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
# SIDEBAR (CONTROL)
# ==========================================================
with st.sidebar:
    st.header("⚙️ Configuración")
    usuarios_lista = sorted(df["Usuario"].dropna().unique().tolist())
    sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
    
    st.markdown("---")
    tipo_mapa = st.radio("Mapa", ["Calle", "Satélite"], label_visibility="collapsed")
    
    st.markdown("---")
    # EL BOTÓN MÁGICO
    modo_pdf = st.checkbox("🖨️ Generar Vista para PDF", value=False)
    
    if st.button("🔄 Actualizar"): st.rerun()

if not sel_usuarios:
    st.stop()

df_f = df[df["Usuario"].isin(sel_usuarios)].copy()

# Cálculos de Estadísticas y Coordenadas para Mapa
stats_list = []
all_coords = []

for usuario in sel_usuarios:
    u_data = df_f[df_f["Usuario"] == usuario]
    dist = 0.0
    coords = u_data[["Latitud", "Longitud"]].values.tolist()
    all_coords.extend(coords)
    
    if len(coords) > 1:
        for i in range(len(coords)-1):
            dist += calcular_distancia(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
            
    stats_list.append({
        "Repartidor": usuario, 
        "Fotos": u_data['url_limpia'].notna().sum(), 
        "Km": f"{dist:.2f}"
    })

# ==========================================================
# RENDERIZADO CONDICIONAL
# ==========================================================

if modo_pdf:
    # ======================================================
    # VISTA REPORTE (PDF / IMPRESIÓN)
    # ======================================================
    
    # CSS PARA LIMPIAR TODO Y DEJAR SOLO EL REPORTE
    st.markdown("""
    <style>
        /* Ocultar interfaz de Streamlit */
        header, footer, [data-testid="stSidebar"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
        
        /* Layout de Impresión */
        @media print {
            @page { size: tabloid landscape; margin: 5mm; }
            body { -webkit-print-color-adjust: exact; }
        }
        
        /* Contenedor Principal Reporte */
        .report-container {
            padding: 20px;
            font-family: sans-serif;
            background: white;
            color: black;
        }
        
        /* Header: Título izq, Stats der */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        
        .header-left { display: flex; align-items: center; }
        .emoji-big { font-size: 60px; margin-right: 20px; }
        .title-text h1 { margin: 0; font-size: 36px; text-transform: uppercase; line-height: 1; }
        .title-text h2 { margin: 0; font-size: 18px; color: #666; font-weight: normal; }
        
        /* Tabla Stats HTML */
        .stats-table { border-collapse: collapse; font-size: 14px; }
        .stats-table th { background: #333; color: white; padding: 5px 15px; text-align: left; }
        .stats-table td { border-bottom: 1px solid #ccc; padding: 5px 15px; }
        
        /* Grid de Fotos Reporte */
        .report-gallery {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 20px;
        }
        .report-photo-item {
            width: 180px; /* Tamaño fijo para impresión */
            border: 1px solid #ccc;
            background: #f9f9f9;
            padding: 5px;
            page-break-inside: avoid; /* Evita que se corten al imprimir */
        }
        .report-photo-item img {
            width: 100%;
            height: auto;
            display: block;
        }
        .report-caption {
            font-size: 10px;
            text-align: center;
            margin-top: 5px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    # 1. HEADER DEL REPORTE (HTML)
    rows_html = ""
    for s in stats_list:
        rows_html += f"<tr><td>{s['Repartidor']}</td><td>{s['Fotos']}</td><td>{s['Km']}</td></tr>"
    
    header_html = f"""
    <div class="report-container">
        <div class="report-header">
            <div class="header-left">
                <div class="emoji-big">🏃🏽‍♂️</div>
                <div class="title-text">
                    <h1>Siguiendo-T</h1>
                    <h2>Reporte de Actividad</h2>
                </div>
            </div>
            <div class="header-right">
                <table class="stats-table">
                    <tr><th>Repartidor</th><th>Fotos</th><th>Km</th></tr>
                    {rows_html}
                </table>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # 2. MAPA GIGANTE (HD)
    # Creamos un mapa limpio sin controles de zoom para que se vea impreso
    m_pdf = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False, attributionControl=False)
    
    if tipo_mapa == "Satélite":
        folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m_pdf)
    
    colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
    
    for i, nombre in enumerate(sel_usuarios):
        color = colores[i % len(colores)]
        u_data = df_f[df_f["Usuario"] == nombre]
        coords = u_data[["Latitud", "Longitud"]].values.tolist()
        
        if len(coords) > 1:
            folium.PolyLine(coords, color=color, weight=5, opacity=0.8).add_to(m_pdf)
            # Flechas
            PolyLineTextPath(folium.PolyLine(coords, color=color), '          ►          ', repeat=True, offset=8, attributes={'fill': color, 'font-size': '12'}).add_to(m_pdf)
        
        # Pines Inicio/Fin
        if not u_data.empty:
            folium.Marker(coords[0], icon=folium.DivIcon(html='<div style="font-size:24pt;">📌</div>')).add_to(m_pdf)
            folium.Marker(coords[-1], icon=folium.DivIcon(html='<div style="font-size:24pt;">🏁</div>')).add_to(m_pdf)
            
            # Miniaturas en mapa PDF (Opcional, a veces saturan, aquí las pongo sutiles)
            for _, r in u_data.iterrows():
                if r['url_limpia']:
                     folium.CircleMarker([r["Latitud"], r["Longitud"]], radius=3, color=color, fill=True).add_to(m_pdf)

    if all_coords:
        m_pdf.fit_bounds(all_coords)

    # Renderizar mapa a ancho completo y alto suficiente
    st_folium(m_pdf, width=1300, height=600, returned_objects=[])
    
    # 3. GALERÍA DE FOTOS (Formato Impresión)
    df_gal = df_f[df_f['url_limpia'].notna()]
    if not df_gal.empty:
        gal_html = '<div class="report-container"><div class="report-gallery">'
        for _, row in df_gal.iterrows():
            url = row['url_limpia']
            user = str(row['Usuario']).split()[0]
            hora = str(row['Hora'])[:5]
            gal_html += f"""
            <div class="report-photo-item">
                <img src="{url}">
                <div class="report-caption">{user} - {hora}</div>
            </div>
            """
        gal_html += '</div></div>'
        st.markdown(gal_html, unsafe_allow_html=True)

else:
    # ======================================================
    # VISTA NORMAL (LA APP INTERACTIVA)
    # ======================================================
    
    # CSS APP NORMAL
    st.markdown("""
    <style>
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    header[data-testid="stHeader"] button { color: var(--text-color) !important; }
    .title-container { display: flex; align-items: center; margin-top: 40px; margin-bottom: 15px; }
    .title-emoji { font-size: clamp(50px, 14vw, 75px); margin-right: 10px; line-height: 1; }
    .title-main { font-weight: 900; font-size: clamp(28px, 8vw, 40px); line-height: 1.0; text-transform: uppercase; }
    .title-sub { font-weight: 600; font-size: clamp(16px, 5vw, 24px); line-height: 1.1; opacity: 0.8; }
    
    /* Galería App */
    .gallery-container { display: flex; flex-wrap: wrap; margin: 0 -4px; }
    .gallery-item { box-sizing: border-box; padding: 4px; width: 25%; }
    @media (max-width: 768px) { .gallery-item { width: 50% !important; } }
    
    .photo-card { border: 1px solid #ddd; border-radius: 6px; background-color: #f0f2f6; overflow: hidden; height: 210px; display: flex; flex-direction: column; }
    .photo-card img { width: 100%; height: 185px; object-fit: contain; background-color: #ababb3; }
    .photo-caption { height: 25px; background: #fff; color: #000; font-size: 10px; font-weight: 600; display: flex; align-items: center; justify-content: center; border-top: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

    # TÍTULO APP
    st.markdown("""
    <div class="title-container">
        <div class="title-emoji">🏃🏽‍♂️</div>
        <div>
            <div class="title-main">Siguiendo-T</div>
            <div class="title-sub">Monitor de Reparto</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📍 Mapa", "☁️ Cierre"])

    with tab1:
        # MAPA APP
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        
        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f["Usuario"] == nombre].reset_index(drop=True)
            if not u_data.empty:
                coords = u_data[["Latitud", "Longitud"]].values.tolist()
                if len(coords) > 1:
                    linea = folium.PolyLine(coords, color=color, weight=4).add_to(m)
                    PolyLineTextPath(linea, '                    ▶                    ', repeat=True, offset=20, attributes={'fill': color, 'font-size': '12'}).add_to(m)
                
                # Pines normales
                for j, row in u_data.iterrows():
                    if row['url_limpia']:
                        popup_html = f'<img src="{row["url_limpia"]}" style="max-width:220px; max-height:220px; object-fit:contain;">'
                        folium.Marker([row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'<div style="width:30px; height:30px; border:2px solid {color}; background:white; border-radius:4px; overflow:hidden;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                            popup=folium.Popup(popup_html, max_width=230)).add_to(m)
                
                # Inicio/Fin
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>')).add_to(m)
                folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>')).add_to(m)

        st_folium(m, width="100%", height=250, returned_objects=[])

        # INFO APP
        st.markdown("### 📊 Estadísticas")
        st.dataframe(pd.DataFrame(stats_list), use_container_width=True, hide_index=True)
        
        st.markdown("### 📸 Evidencias")
        df_gal = df_f[df_f['url_limpia'].notna()]
        if not df_gal.empty:
            html_parts = ['<div class="gallery-container">']
            for _, row in df_gal.iterrows():
                url = row['url_limpia']
                user = str(row['Usuario']).split()[0].replace("<","").replace(">","")
                hora = str(row['Hora'])[:5]
                html_parts.append(f'<div class="gallery-item"><a href="{url}" target="_blank" style="text-decoration:none;"><div class="photo-card"><img src="{url}" loading="lazy"><div class="photo-caption">{user} {hora}</div></div></a></div>')
            html_parts.append('</div>')
            st.markdown("".join(html_parts), unsafe_allow_html=True)

    with tab2:
        st.header("Cierre")
        if st.button("🚀 Archivar Día", type="primary"):
            st.success("Completado")
