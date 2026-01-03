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

# --- CSS PARA FORZAR 2 COLUMNAS REALES EN MÓVIL ---
st.markdown("""
    <style>
    /* 1. Limpieza de Interfaz */
    header[data-testid="stHeader"] { background: transparent !important; }
    header[data-testid="stHeader"] button { color: var(--text-color) !important; }
    footer {display: none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    
    /* 2. Título Adaptable */
    .titulo-smart {
        margin-left: 40px; margin-top: 10px;
        font-weight: bold; white-space: nowrap;
        font-size: clamp(18px, 6vw, 26px);
        color: var(--text-color);
    }
    
    /* 3. LA CLAVE PARA 2 COLUMNAS EN MÓVIL */
    /* Streamlit por defecto pone min-width: auto en móvil, lo que lo manda a 100%. */
    /* Nosotros forzamos que el ancho mínimo sea pequeño para que quepan dos. */
    
    [data-testid="column"] {
        width: calc(50% - 10px) !important;
        flex: 1 1 calc(50% - 10px) !important;
        min-width: calc(50% - 10px) !important;
    }
    
    /* Ajuste para que las imágenes no tengan márgenes raros */
    [data-testid="stImage"] {
        margin-bottom: 0px;
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
    # Prioridad: Objeto de Airtable (Lista de dicts)
    if isinstance(valor, list) and len(valor) > 0 and isinstance(valor[0], dict):
        return valor[0].get("url")
    # Fallback: String
    val_str = str(valor).strip()
    if val_str.lower() in ['nan', 'none', '', '[]']: return None
    if val_str.startswith('http'): return val_str
    # Fallback: Regex
    if '(' in val_str and ')' in val_str:
        urls = re.findall(r'\((https?://[^\)]+)\)', val_str)
        if urls: return urls[0]
    return None

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
    
    # Limpieza
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud"])
    
    # --- ORDEN CRONOLÓGICO (CRUCIAL) ---
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    df = df.sort_values("Hora_dt")  # Ordenamos TODO el dataframe aquí
    
    # URLs
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
                    # Ruta
                    coords = u_data[["Latitud", "Longitud"]].values.tolist()
                    dist_u = 0.0
                    if len(coords) > 1:
                        linea = folium.PolyLine(coords, color=color, weight=4).add_to(m)
                        PolyLineTextPath(linea, '   ►   ', repeat=True, offset=8, attributes={'fill': color, 'font-size': '18'}).add_to(m)

                    ult_hito = None
                    for j, row in u_data.iterrows():
                        if j < len(u_data) - 1:
                            dist_u += calcular_distancia(row["Latitud"], row["Longitud"], u_data.iloc[j+1]["Latitud"], u_data.iloc[j+1]["Longitud"])
                        
                        # Pin 15 mins
                        if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                            folium.Marker([row["Latitud"], row["Longitud"]], 
                                          icon=folium.DivIcon(html=f'<div style="font-size:18pt;">📍</div>'),
                                          popup=folium.Popup(f"{nombre}<br>{row['Hora']}", max_width=150)).add_to(m)
                            ult_hito = row["Hora_dt"]
                        
                        # Miniatura
                        if row['url_limpia']:
                            folium.Marker([row["Latitud"], row["Longitud"]],
                                icon=folium.DivIcon(html=f'<div style="width:40px; height:40px; border:2px solid {color}; border-radius:4px; overflow:hidden;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                                popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="150">', max_width=150)).add_to(m)

                    # Inicio / Fin
                    r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                    off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
                    folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}", z_index_offset=2000).add_to(m)
                    folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}", z_index_offset=2000).add_to(m)
                    
                    resumen_jornada.append({"Repartidor": nombre, "📸": u_data['url_limpia'].notna().sum(), "Dist.": f"{dist_u:.2f} km"})

            st_folium(m, width="100%", height=400, returned_objects=[])

            st.markdown("---")
            st.write("**📊 Resumen**")
            st.dataframe(pd.DataFrame(resumen_jornada), use_container_width=True, hide_index=True)
            
            st.write("**📸 Evidencias (Cronológico)**")
            
            df_gal = df_f[df_f['url_limpia'].notna()]
            
            if not df_gal.empty:
                # AQUÍ LA SOLUCIÓN SEGURA:
                # 1. Usamos st.columns(2).
                # 2. El CSS de arriba fuerza que [data-testid="column"] sea ~50% de ancho.
                # 3. Usamos st.image nativo (no HTML) para que no falle el renderizado.
                
                cols = st.columns(2) 
                for i, (_, row) in enumerate(df_gal.iterrows()):
                    with cols[i % 2]:
                        # Nombre corto para móvil
                        nombre_corto = row['Usuario'].split()[0] if row['Usuario'] else "Repartidor"
                        st.image(row['url_limpia'], caption=f"{nombre_corto} {row['Hora'][:5]}", use_container_width=True)

with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
