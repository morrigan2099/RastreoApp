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

# --- CSS RESPONSIVO AVANZADO ---
st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit */
    header[data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }
    header[data-testid="stHeader"] button { color: var(--text-color) !important; }
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display:none;}
    .block-container { padding-top: 2rem !important; }

    /* Título que se adapta al ancho de pantalla (Viewport Width) */
    .titulo-placeholder {
        width: 100%;
        text-align: left;
        margin-left: 35px;
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        /* font-size: 5.5vw ajusta el texto al ancho del móvil */
        font-size: clamp(16px, 5.5vw, 28px);
        color: var(--text-color);
    }

    /* FORZAR GRID DE 2 COLUMNAS EN MÓVIL (A prueba de balas) */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: flex-start !important;
        }
        div[data-testid="column"] {
            width: calc(50% - 8px) !important; /* Fuerza 2 por fila */
            flex: 1 1 calc(50% - 8px) !important;
            min-width: calc(50% - 8px) !important;
            margin-bottom: 10px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================================
# CARGA DE CREDENCIALES (SECRETS)
# ==========================================================
try:
    AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]
    AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    AIRTABLE_TABLE_NAME = st.secrets["AIRTABLE_TABLE_NAME"]
    
    cloudinary.config(
        cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key=st.secrets["CLOUDINARY_API_KEY"],
        api_secret=st.secrets["CLOUDINARY_API_SECRET"]
    )
    
    g_creds = dict(st.secrets["google_creds"])
    g_creds["private_key"] = g_creds["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        g_creds, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
except Exception as e:
    st.error(f"❌ Error en Secrets: {e}")
    st.stop()

# ==========================================================
# FUNCIONES
# ==========================================================
def obtener_url_final(valor):
    if not valor or str(valor).lower() in ['nan', 'none', '', '[]']:
        return None
    val_str = str(valor).strip()
    if '(' in val_str and ')' in val_str:
        urls = re.findall(r'\((https?://[^\)]+)\)', val_str)
        if urls: return urls[0]
    if val_str.startswith('http'): return val_str
    if isinstance(valor, list) and len(valor) > 0:
        return valor[0].get("url")
    return None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# UI - MONITOR 🗞️
# ==========================================================
# Placeholder de título dinámico
st.markdown('<div class="titulo-placeholder">🗞️ Monitor de Reparto Folletos</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📍 Mapa de Ruta", "☁️ Cierre de Jornada"])

with tab1:
    records = table.all()
    if not records:
        st.warning("Sin datos.")
        st.stop()

    df = pd.DataFrame([r["fields"] for r in records])
    df.columns = [c.lower() for c in df.columns]
    
    rename = {c: "Latitud" if "lat" in c else "Longitud" if "lon" in c else "Usuario" if "usu" in c else "Hora" if "hora" in c else "Foto" if ("foto" in c and "etiq" not in c) else "Tipo" if "tipo" in c else c for c in df.columns}
    df = df.rename(columns=rename)
    
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud"])
    df["Usuario"] = df["Usuario"].astype(str).str.strip()
    df["Hora_dt"] = pd.to_datetime(df["Hora"], format='%H:%M:%S', errors="coerce")
    df["url_limpia"] = df["Foto"].apply(obtener_url_final)

    with st.sidebar:
        st.header("⚙️ Filtros")
        usuarios_lista = sorted(df["Usuario"].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"): st.rerun()

    if sel_usuarios:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
        
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        resumen_jornada = []

        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f["Usuario"] == nombre].sort_values("Hora_dt").reset_index(drop=True)
            
            if not u_data.empty:
                coords = u_data[["Latitud", "Longitud"]].values.tolist()
                dist_u = 0.0
                
                if len(coords) > 1:
                    linea = folium.PolyLine(coords, color=color, weight=4, opacity=0.8).add_to(m)
                    PolyLineTextPath(linea, '                ►                ', repeat=True, offset=8, attributes={'fill': color, 'font-weight': 'bold', 'font-size': '22', 'stroke': 'black', 'stroke-width': '1'}).add_to(m)

                ult_hito = None
                for j, row in u_data.iterrows():
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        dist_u += calcular_distancia(row["Latitud"], row["Longitud"], p_next["Latitud"], p_next["Longitud"])

                    if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                        folium.Marker([row["Latitud"], row["Longitud"]], icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:20pt; filter: drop-shadow(1px 1px 2px black);">📍</div></div>'), z_index_offset=1000).add_to(m)
                        ult_hito = row["Hora_dt"]

                    if row['url_limpia']:
                        folium.Marker(
                            [row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'<div style="width:50px; height:50px; border:3px solid {color}; background:white; box-shadow:2px 2px 6px black; border-radius:6px; overflow:hidden; display:flex;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover; transform:scale(1.4);"></div>'),
                            popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="150">', max_width=150)
                        ).add_to(m)

                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                mismo_sitio = (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005)
                off = 0.00009 if mismo_sitio else 0

                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:22pt; filter: drop-shadow(2px 2px 2px black);">📌</div></div>'), z_index_offset=2000).add_to(m)
                folium.Marker([r_fin["Latitud"] + off, r_fin["Longitud"] + off], icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:22pt; filter: drop-shadow(2px 2px 2px black);">🏁</div></div>'), z_index_offset=2000).add_to(m)

                resumen_jornada.append({"Repartidor": nombre, "📸": u_data['url_limpia'].notna().sum(), "Dist.": f"{dist_u:.2f} km"})

        st_folium(m, width="100%", height=450, returned_objects=[])

        st.markdown("---")
        st.write("**📊 Resumen**")
        st.dataframe(pd.DataFrame(resumen_jornada), use_container_width=True, hide_index=True)
        
        st.write("**📸 Evidencias (Orden Cronológico)**")
        # --- FILTRO Y ORDEN CRONOLÓGICO ---
        df_gal = df_f[df_f['url_limpia'].notna()].sort_values("Hora_dt")
        
        if not df_gal.empty:
            # En escritorio st.columns(4) funciona bien.
            # En móvil, el CSS inyectado arriba forzará que esto se vea como 2 columnas.
            cols = st.columns(4) 
            for i, (_, row) in enumerate(df_gal.iterrows()):
                with cols[i % 4]:
                    st.image(row['url_limpia'], caption=f"{row['Usuario'].split()[0]} {row['Hora'][:5]}", use_container_width=True)

with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
