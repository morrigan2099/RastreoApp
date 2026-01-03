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

# ==========================================================
# CSS ESTRATÉGICO
# ==========================================================
st.markdown("""
<style>
/* 1. SIDEBAR VISIBLE PERO LIMPIO */
header[data-testid="stHeader"] {
    background: transparent !important;
    z-index: 1 !important;
}
/* Asegurar que el botón del menú tenga color visible */
header[data-testid="stHeader"] button {
    color: var(--text-color) !important; 
}
/* Ocultar solo la decoración roja, no el header completo */
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }

/* 2. TÍTULO MÓVIL */
.titulo-smart {
    margin-left: 50px; /* Espacio para el botón del menú */
    margin-top: 10px;
    font-weight: bold;
    font-size: clamp(18px, 6vw, 26px);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* 3. GRID MÁGICO PARA MÓVIL (2 COLUMNAS) */
/* En escritorio se respetan las 4 columnas de Python. 
   En móvil, forzamos al CSS a que cada columna mida el 50% */
@media (max-width: 768px) {
    div[data-testid="column"] {
        width: 50% !important;
        flex: 0 0 50% !important;
        min-width: 50% !important;
    }
    /* Ajuste para que las filas no se rompan raro */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
}

/* 4. IMÁGENES LIMPIAS */
div[data-testid="stImage"] {
    margin-bottom: 10px;
}
div[data-testid="stImage"] > img {
    border-radius: 8px;
    /* Esto asegura que la imagen se vea completa y proporcional */
    object-fit: contain !important; 
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
    
    # Cloudinary & Google (Si los necesitas para el cierre)
    cloudinary.config(
        cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key=st.secrets["CLOUDINARY_API_KEY"],
        api_secret=st.secrets["CLOUDINARY_API_SECRET"]
    )
    g_creds = dict(st.secrets["google_creds"])
    g_creds["private_key"] = g_creds["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(g_creds, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    
    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
except Exception as e:
    st.error(f"❌ Error de Conexión: {e}")
    st.stop()

# ==========================================================
# FUNCIONES
# ==========================================================
def obtener_url_final(valor):
    if not valor: return None
    # Prioridad: Objeto Airtable
    if isinstance(valor, list) and len(valor) > 0 and isinstance(valor[0], dict):
        return valor[0].get("url")
    # Fallback: String
    val_str = str(valor).strip()
    if val_str.lower() in ['nan', 'none', '', '[]']: return None
    if val_str.startswith('http'): return val_str
    # Fallback: Regex
    urls = re.findall(r'(https?://[^\s\)]+)', val_str)
    return urls[0] if urls else None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# INTERFAZ
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
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    
    # ORDEN CRONOLÓGICO IMPORTANTE
    df = df.sort_values("Hora_dt")
    
    if "Foto" in df.columns:
        df["url_limpia"] = df["Foto"].apply(obtener_url_final)
    else:
        df["url_limpia"] = None

    with st.sidebar:
        st.header("⚙️ Config")
        usuarios_lista = sorted(df["Usuario"].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"): st.rerun()

    if sel_usuarios:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        
        # --- LÓGICA DE MAPA Y ESTADÍSTICAS ---
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        stats_list = [] # Para la tabla de estadísticas

        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f["Usuario"] == nombre].reset_index(drop=True)
            
            if not u_data.empty:
                dist_u = 0.0
                coords = u_data[["Latitud", "Longitud"]].values.tolist()
                
                # Ruta
                if len(coords) > 1:
                    linea = folium.PolyLine(coords, color=color, weight=4).add_to(m)
                    PolyLineTextPath(linea, '   ►   ', repeat=True, offset=8, attributes={'fill': color, 'font-size': '18'}).add_to(m)

                ult_hito = None
                for j, row in u_data.iterrows():
                    # Calculo distancia
                    if j < len(u_data) - 1:
                        dist_u += calcular_distancia(row["Latitud"], row["Longitud"], u_data.iloc[j+1]["Latitud"], u_data.iloc[j+1]["Longitud"])
                    
                    # Pin 15 mins
                    if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                        folium.Marker([row["Latitud"], row["Longitud"]], 
                                      icon=folium.DivIcon(html=f'<div style="font-size:18pt;">📍</div>'),
                                      popup=f"{nombre}<br>{row['Hora']}").add_to(m)
                        ult_hito = row["Hora_dt"]
                    
                    # Miniatura Mapa
                    if row['url_limpia']:
                        folium.Marker([row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'<div style="width:40px; height:40px; border:2px solid {color}; border-radius:4px; overflow:hidden;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                            popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="150">', max_width=150)).add_to(m)

                # Inicio / Fin
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}").add_to(m)
                folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}").add_to(m)
                
                # Guardar Stats
                stats_list.append({
                    "Repartidor": nombre,
                    "Fotos": u_data['url_limpia'].notna().sum(),
                    "Distancia": f"{dist_u:.2f} km"
                })

        st_folium(m, width="100%", height=420, returned_objects=[])

        # --- SECCIÓN DE ESTADÍSTICAS ---
        st.markdown("### 📊 Estadísticas")
        st.dataframe(pd.DataFrame(stats_list), use_container_width=True, hide_index=True)
        
        # --- GALERÍA NATIVA (Estable) ---
        st.markdown("### 📸 Evidencias")
        df_gal = df_f[df_f['url_limpia'].notna()]
        
        if not df_gal.empty:
            # Usamos st.columns(4) para escritorio.
            # El CSS arriba fuerza width: 50% en móvil para crear el efecto 2x2.
            cols = st.columns(4)
            for i, (_, row) in enumerate(df_gal.iterrows()):
                with cols[i % 4]:
                    nombre = row['Usuario'].split()[0] if row['Usuario'] else ""
                    # use_container_width=True ajusta la imagen al ancho de la columna
                    # Como no pusimos CSS de aspect-ratio forzado, la imagen guarda su proporción (reducción proporcional)
                    st.image(row['url_limpia'], caption=f"{nombre} {row['Hora'][:5]}", use_container_width=True)

with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
