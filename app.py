import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import json
import folium
import math
import re
from streamlit_folium import st_folium
from folium.plugins import PolyLineTextPath

# ==========================================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================================
st.set_page_config(page_title="Monitor 🗞️", layout="wide")

# CSS: Título, Grid HTML y Limpieza
st.markdown("""
    <style>
    /* Interfaz Limpia */
    header[data-testid="stHeader"] { background: transparent !important; }
    header[data-testid="stHeader"] button { color: var(--text-color) !important; }
    footer {display: none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    
    /* Título */
    .titulo-smart {
        margin-left: 40px; margin-top: 10px;
        font-weight: bold; white-space: nowrap;
        font-size: clamp(18px, 6vw, 26px);
        color: var(--text-color);
    }
    
    /* --- CSS GRID ROBUSTO (Para que no se rompa) --- */
    .galeria-wrapper {
        display: grid;
        grid-template-columns: repeat(2, 1fr); /* MÓVIL: 2 COLUMNAS FIJAS */
        gap: 10px;
        padding: 10px 0;
        width: 100%;
        box-sizing: border-box;
    }
    
    /* ESCRITORIO: Cambia a 4 columnas */
    @media (min-width: 769px) {
        .galeria-wrapper { grid-template-columns: repeat(4, 1fr); }
    }

    /* CARD INDIVIDUAL */
    .foto-box {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-decoration: none !important; /* Quitar subrayado de links */
    }
    
    /* IMAGEN */
    .foto-box img {
        width: 100%;
        height: auto;
        aspect-ratio: 1 / 1; /* Cuadrada para orden */
        object-fit: cover;   /* Llenar el cuadro */
        display: block;
    }
    
    /* TEXTO PIE DE FOTO */
    .foto-info {
        font-size: 11px;
        padding: 5px;
        text-align: center;
        color: #333;
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-family: sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

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
    if '(' in val_str and ')' in val_str:
        urls = re.findall(r'\((https?://[^\)]+)\)', val_str)
        if urls: return urls[0]
    return None

def limpiar_texto(texto):
    """Elimina caracteres que rompen el HTML"""
    if not texto: return ""
    return str(texto).replace('"', '').replace("'", "").replace("<", "").replace(">", "")

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# UI
# ==========================================================
st.markdown('<div class="titulo-smart">🗞️ Monitor Reparto Folletos</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📍 Mapa", "☁️ Cierre"])

with tab1:
    records = table.all()
    if not records:
        st.warning("Sin datos.")
        st.stop()

    df = pd.DataFrame([r["fields"] for r in records])
    df.columns = [c.lower() for c in df.columns]
    rename = {c: "Latitud" if "lat" in c else "Longitud" if "lon" in c else "Usuario" if "usu" in c else "Hora" if "hora" in c else "Foto" if ("foto" in c and "etiq" not in c) else c for c in df.columns}
    df = df.rename(columns=rename)
    
    # Procesamiento inicial
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud"])
    
    # 1. ORDEN CRONOLÓGICO PRIMERO
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    df = df.sort_values("Hora_dt")
    
    # 2. Obtener URLs
    if "Foto" in df.columns:
        df["url_limpia"] = df["Foto"].apply(obtener_url_final)
    else:
        df["url_limpia"] = None

    with st.sidebar:
        usuarios_lista = sorted(df["Usuario"].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"): st.rerun()

    if sel_usuarios:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        
        # --- MAPA ---
        if not df_f.empty:
            m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
            if tipo_mapa == "Satélite":
                folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

            colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
            resumen_jornada = []

            for i, nombre in enumerate(sel_usuarios):
                color = colores[i % len(colores)]
                u_data = df_f[df_f["Usuario"] == nombre].reset_index(drop=True)
                
                if not u_data.empty:
                    coords = u_data[["Latitud", "Longitud"]].values.tolist()
                    dist_u = 0.0
                    if len(coords) > 1:
                        linea = folium.PolyLine(coords, color=color, weight=4).add_to(m)
                        PolyLineTextPath(linea, '   ►   ', repeat=True, offset=8, attributes={'fill': color, 'font-size': '18'}).add_to(m)

                    ult_hito = None
                    for j, row in u_data.iterrows():
                        if j < len(u_data) - 1:
                            dist_u += calcular_distancia(row["Latitud"], row["Longitud"], u_data.iloc[j+1]["Latitud"], u_data.iloc[j+1]["Longitud"])
                        
                        if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                            folium.Marker([row["Latitud"], row["Longitud"]], 
                                          icon=folium.DivIcon(html=f'<div style="font-size:18pt;">📍</div>'),
                                          popup=f"{nombre}<br>{row['Hora']}", max_width=150).add_to(m)
                            ult_hito = row["Hora_dt"]
                        
                        if row['url_limpia']:
                            folium.Marker([row["Latitud"], row["Longitud"]],
                                icon=folium.DivIcon(html=f'<div style="width:40px; height:40px; border:2px solid {color}; border-radius:4px; overflow:hidden;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                                popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="150">', max_width=150)).add_to(m)

                    r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                    off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
                    folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}", z_index_offset=2000).add_to(m)
                    folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}", z_index_offset=2000).add_to(m)
                    
                    resumen_jornada.append({"Repartidor": nombre, "📸": u_data['url_limpia'].notna().sum(), "Dist.": f"{dist_u:.2f} km"})

            st_folium(m, width="100%", height=400, returned_objects=[])

            st.markdown("---")
            st.write("**📊 Resumen**")
            st.dataframe(pd.DataFrame(resumen_jornada), use_container_width=True, hide_index=True)
            
            # --- GALERÍA HTML ROBUSTA ---
            st.write("**📸 Evidencias (Cronológico)**")
            df_gal = df_f[df_f['url_limpia'].notna()]
            
            if not df_gal.empty:
                # Construimos el HTML con cuidado
                html_code = '<div class="galeria-wrapper">'
                
                for _, row in df_gal.iterrows():
                    nombre_limpio = limpiar_texto(row['Usuario'].split()[0])
                    hora_limpia = limpiar_texto(row['Hora'][:5])
                    url_img = row['url_limpia']
                    
                    # CADA CARD
                    html_code += f'''
                    <a class="foto-box" href="{url_img}" target="_blank">
                        <img src="{url_img}" loading="lazy">
                        <div class="foto-info">{nombre_limpio} {hora_limpia}</div>
                    </a>
                    '''
                
                html_code += '</div>'
                
                # Renderizamos TODO el bloque junto
                st.markdown(html_code, unsafe_allow_html=True)
            else:
                st.info("Sin evidencias.")

with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
