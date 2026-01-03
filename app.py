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
# CARGA DE CREDENCIALES DESDE SECRETS
# ==========================================================
try:
    # Airtable
    AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]
    AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    AIRTABLE_TABLE_NAME = st.secrets["AIRTABLE_TABLE_NAME"]
    
    # Cloudinary
    cloudinary.config(
        cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key=st.secrets["CLOUDINARY_API_KEY"],
        api_secret=st.secrets["CLOUDINARY_API_SECRET"]
    )
    
    # Google Sheets
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
    st.error(f"❌ Error cargando Secrets: {e}")
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
# UI INTERFAZ
# ==========================================================
st.title("🚚 Monitor de Reparto Pro")
tab1, tab2 = st.tabs(["📍 Mapa de Ruta", "☁️ Cierre de Jornada"])

with tab1:
    if st.button("🔄 Refrescar Datos"):
        st.rerun()

    records = table.all()
    if not records:
        st.warning("No hay datos en vivo.")
        st.stop()

    # Procesamiento
    df = pd.DataFrame([r["fields"] for r in records])
    df.columns = [c.lower() for c in df.columns]
    
    # Mapeo de columnas
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
        tipo_mapa = st.radio("Capa de Mapa", ["Calle", "Satélite"])
        modo_reporte = st.checkbox("📑 Mostrar Resumen y Galería", value=True)

    if not sel_usuarios:
        st.info("Selecciona un repartidor.")
    else:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
        
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
        else:
            folium.TileLayer('OpenStreetMap').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        resumen_final = []

        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f["Usuario"] == nombre].sort_values("Hora_dt").reset_index(drop=True)
            dist_total = 0.0
            
            if not u_data.empty:
                coords = u_data[["Latitud", "Longitud"]].values.tolist()
                
                # RUTA (GLOW + FLECHAS REDUCIDAS)
                if len(coords) > 1:
                    folium.PolyLine(coords, color='black', weight=7, opacity=0.3).add_to(m)
                    linea = folium.PolyLine(coords, color=color, weight=3).add_to(m)
                    # "►" reducido a un cuarto (más espacio en el string)
                    PolyLineTextPath(linea, '                                ►                                ', 
                                     repeat=True, offset=8, 
                                     attributes={'fill': color, 'font-weight': 'bold', 'font-size': '20', 'stroke': 'black', 'stroke-width': '0.5'}).add_to(m)

                ult_hito = None
                for j in range(len(u_data)):
                    row = u_data.iloc[j]
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        dist_total += calcular_distancia(row["Latitud"], row["Longitud"], p_next["Latitud"], p_next["Longitud"])

                    # HITOS 15 MIN 📍
                    if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                        folium.Marker([row["Latitud"], row["Longitud"]], 
                            icon=folium.DivIcon(html=f'''<div style="text-align:center;"><div style="font-size:16pt; filter: drop-shadow(1px 1px 2px black);">📍</div><div style="font-size:8pt; color:white; background:rgba(0,0,0,0.7); padding:2px 4px; border-radius:3px; font-weight:bold;">{row["Hora"][:5]}</div></div>'''),
                            popup=f"Hora: {row['Hora']}").add_to(m)
                        ult_hito = row["Hora_dt"]

                    # MINIATURAS ZOOM
                    if row['url_limpia']:
                        folium.Marker([row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'''<div style="width:55px; height:55px; border:3px solid {color}; background:white; box-shadow:3px 3px 6px black; border-radius:4px; overflow:hidden;"><img src="{row['url_limpia']}" width="55" height="55" style="object-fit:cover; transform: scale(1.1);"></div>'''),
                            popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="250">', max_width=250)).add_to(m)

                # INICIO (📌) Y FIN (🏁) — EVITAR SOBREPOSICIÓN
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                is_same = (r_ini["Latitud"] == r_fin["Latitud"] and r_ini["Longitud"] == r_fin["Longitud"])
                offset = 0.00005 if is_same else 0 # Pequeño desvío si coinciden

                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], 
                    icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:26pt; filter: drop-shadow(2px 2px 3px black);">📌</div><div style="font-size:8pt; color:white; background:green; padding:1px 3px; border-radius:3px; font-weight:bold;">{r_ini["Hora"][:5]}</div></div>'),
                    popup=f"SALIDA: {r_ini['Hora']}").add_to(m)
                
                folium.Marker([r_fin["Latitud"] + offset, r_fin["Longitud"] + offset], 
                    icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:26pt; filter: drop-shadow(2px 2px 3px black);">🏁</div><div style="font-size:8pt; color:white; background:black; padding:1px 3px; border-radius:3px; font-weight:bold;">{r_fin["Hora"][:5]}</div></div>'),
                    popup=f"LLEGADA: {r_fin['Hora']}").add_to(m)

                resumen_final.append({"Repartidor": nombre, "Salida": r_ini["Hora"], "Llegada": r_fin["Hora"], "📸": u_data['url_limpia'].notna().sum(), "KM": f"{dist_total:.2f} km"})

        m.fit_bounds(df_f[["Latitud", "Longitud"]].values.tolist())
        st_folium(m, width="100%", height=600, returned_objects=[])

        if modo_reporte:
            st.markdown("### 📋 Resumen y 📸 Galería")
            st.table(pd.DataFrame(resumen_final))
            df_gal = df_f[df_f['url_limpia'].notna()]
            if not df_gal.empty:
                cols = st.columns(2) # 2 columnas para mejor vista en móvil
                for idx, (_, f_row) in enumerate(df_gal.iterrows()):
                    with cols[idx % 2]:
                        st.image(f_row['url_limpia'], caption=f"{f_row['Usuario']} ({f_row['Hora']})")

with tab2:
    st.header("☁️ Cierre de Jornada")
    if st.button("🚀 Procesar y Archivar", type="primary"):
        st.success("✅ Cierre completado")
