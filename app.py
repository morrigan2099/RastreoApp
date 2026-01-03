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
st.set_page_config(page_title="Monitor de Reparto Pro", layout="wide")

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
# UI - MONITOR
# ==========================================================
st.title("🚚 Monitor de Reparto Pro")
tab1, tab2 = st.tabs(["📍 Mapa de Ruta", "☁️ Cierre de Jornada"])

with tab1:
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

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
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    df["url_limpia"] = df["Foto"].apply(obtener_url_final)

    with st.sidebar:
        st.header("⚙️ Filtros")
        usuarios_lista = sorted(df["Usuario"].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        modo_reporte = st.checkbox("📑 Activar Reporte y Galería", value=True)

    if sel_usuarios:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15)
        
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
                
                # 1. RUTA (FLECHAS 1/4)
                if len(coords) > 1:
                    linea = folium.PolyLine(coords, color=color, weight=4, opacity=0.8).add_to(m)
                    PolyLineTextPath(linea, '                                ►                                ', 
                                     repeat=True, offset=8, 
                                     attributes={'fill': color, 'font-weight': 'bold', 'font-size': '22', 'stroke': 'black', 'stroke-width': '1'}).add_to(m)

                # 2. MINIATURAS HD Y KM
                for j, row in u_data.iterrows():
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        dist_u += calcular_distancia(row["Latitud"], row["Longitud"], p_next["Latitud"], p_next["Longitud"])

                    if row['url_limpia']:
                        # Ajuste leve de la foto si está en los extremos
                        img_off = 0.00005 if (j == 0 or j == len(u_data)-1) else 0
                        folium.Marker(
                            [row["Latitud"] - img_off, row["Longitud"] - img_off],
                            icon=folium.DivIcon(html=f'''
                                <div style="width:55px; height:55px; border:3px solid {color}; background:white; box-shadow:2px 2px 6px black; border-radius:6px; overflow:hidden; display:flex;">
                                    <img src="{row['url_limpia']}" style="width:100%; height:100%; object-fit:cover; transform:scale(1.4);">
                                </div>'''),
                            popup=folium.Popup(f'<b>{nombre}</b><br><img src="{row["url_limpia"]}" width="200">', max_width=200),
                            z_index_offset=100
                        ).add_to(m)

                # 3. INICIO Y FIN (OFFSET REDUCIDO A 1/5)
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                mismo_sitio = (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005 and abs(r_ini["Longitud"] - r_fin["Longitud"]) < 0.00005)
                
                # Un quinto de la distancia anterior (9 metros aprox)
                off = 0.00009 if mismo_sitio else 0

                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], 
                    icon=folium.DivIcon(html=f'<div style="font-size:24pt; filter:drop-shadow(2px 2px 2px black);">📌</div>'),
                    popup=f"SALIDA: {r_ini['Hora']}", z_index_offset=2000).add_to(m)
                
                folium.Marker([r_fin["Latitud"] + off, r_fin["Longitud"] + off], 
                    icon=folium.DivIcon(html=f'<div style="font-size:24pt; filter:drop-shadow(2px 2px 2px black);">🏁</div>'),
                    popup=f"LLEGADA: {r_fin['Hora']}", z_index_offset=2000).add_to(m)

                resumen_jornada.append({
                    "Repartidor": nombre,
                    "Salida": r_ini["Hora"],
                    "Llegada": r_fin["Hora"],
                    "📸": u_data['url_limpia'].notna().sum(),
                    "Distancia": f"{dist_u:.2f} km"
                })

        m.fit_bounds(df_f[["Latitud", "Longitud"]].values.tolist())
        st_folium(m, width="100%", height=600, returned_objects=[])

        # --- REPORTE Y GALERÍA ---
        if modo_reporte:
            st.markdown("### 📋 Resumen de Jornada")
            st.table(pd.DataFrame(resumen_jornada))
            
            st.markdown("### 📸 Galería de Testigos")
            df_gal = df_f[df_f['url_limpia'].notna()]
            if not df_gal.empty:
                cols = st.columns(2)
                for idx, (_, f_row) in enumerate(df_gal.iterrows()):
                    with cols[idx % 2]:
                        st.image(f_row['url_limpia'], caption=f"{f_row['Usuario']} – {f_row['Hora']}")
