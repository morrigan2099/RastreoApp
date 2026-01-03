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
st.set_page_config(page_title="Monitor 🗞️", layout="wide")

# ==========================================================
# CSS MAESTRO
# ==========================================================
st.markdown("""
<style>
/* 1. SIDEBAR Y LIMPIEZA */
header[data-testid="stHeader"] { background: transparent !important; }
header[data-testid="stHeader"] button { color: var(--text-color) !important; }
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }

/* 2. TÍTULO */
.titulo-smart {
    margin-left: 50px; margin-top: 10px;
    font-weight: bold; font-size: clamp(18px, 6vw, 26px);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    color: var(--text-color);
}

/* 3. GALERÍA GRID FLEXIBLE */
.gallery-container {
    display: flex;
    flex-wrap: wrap;
    margin: 0 -4px; /* Compensar padding */
    justify-content: flex-start;
}

.gallery-item {
    box-sizing: border-box;
    padding: 4px;
    /* ESCRITORIO: 4 Columnas (25%) */
    width: 25%;
}

/* MÓVIL: 2 COLUMNAS (50%) */
@media (max-width: 768px) {
    .gallery-item {
        width: 50% !important;
    }
}

/* 4. TARJETA DE FOTO */
.photo-card {
    border: 1px solid #ddd;
    border-radius: 6px;
    background-color: #f5f5f5; /* Fondo gris claro */
    overflow: hidden;
    height: 200px; /* Altura fija para uniformidad */
    position: relative;
    display: flex;
    flex-direction: column;
}

.photo-card img {
    width: 100%;
    height: 175px; /* Espacio para imagen */
    object-fit: contain; /* <--- NO RECORTA, AJUSTA */
    background-color: #333; /* Fondo oscuro detrás de la foto */
}

.photo-caption {
    height: 25px;
    background: #fff;
    color: #000;
    font-size: 10px;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    border-top: 1px solid #ccc;
    white-space: nowrap;
    overflow: hidden;
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
    urls = re.findall(r'(https?://[^\s\)]+)', val_str)
    return urls[0] if urls else None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
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
    
    # Procesamiento
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud"])
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    df = df.sort_values("Hora_dt")
    
    if "Foto" in df.columns:
        df["url_limpia"] = df["Foto"].apply(obtener_url_final)
    else:
        df["url_limpia"] = None

    with st.sidebar:
        st.header("⚙️ Config")
        usuarios_lista = sorted(df["Usuario"].dropna().unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"): st.rerun()

    if sel_usuarios:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()
        
        # --- MAPA ---
        m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15, zoom_control=False)
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        stats_list = []

        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f["Usuario"] == nombre].reset_index(drop=True)
            
            if not u_data.empty:
                dist_u = 0.0
                coords = u_data[["Latitud", "Longitud"]].values.tolist()
                
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
                                      popup=f"{nombre}<br>{row['Hora']}").add_to(m)
                        ult_hito = row["Hora_dt"]
                    
                    if row['url_limpia']:
                         folium.Marker([row["Latitud"], row["Longitud"]], icon=folium.DivIcon(html=f'<div style="width:30px; height:30px; border:2px solid {color}; background:white;"><img src="{row["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>')).add_to(m)

                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
                folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}").add_to(m)
                folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}").add_to(m)
                
                stats_list.append({"Repartidor": nombre, "Fotos": u_data['url_limpia'].notna().sum(), "Dist.": f"{dist_u:.2f} km"})

        st_folium(m, width="100%", height=400, returned_objects=[])

        # --- ESTADÍSTICAS ---
        st.markdown("### 📊 Estadísticas")
        st.dataframe(pd.DataFrame(stats_list), use_container_width=True, hide_index=True)
        
        # --- GALERÍA HTML (CORREGIDA SIN ESPACIOS ROTOS) ---
        st.markdown("### 📸 Evidencias")
        df_gal = df_f[df_f['url_limpia'].notna()]
        
        if not df_gal.empty:
            # Construcción limpia del string HTML
            html_parts = ['<div class="gallery-container">']
            
            for _, row in df_gal.iterrows():
                url = row['url_limpia']
                user = str(row['Usuario']).split()[0].replace("<","").replace(">","")
                hora = str(row['Hora'])[:5]
                # Todo en una línea para evitar bug de Markdown "Code Block"
                html_parts.append(f'<div class="gallery-item"><a href="{url}" target="_blank" style="text-decoration:none;"><div class="photo-card"><img src="{url}"><div class="photo-caption">{user} {hora}</div></div></a></div>')
            
            html_parts.append('</div>')
            
            # Unir sin saltos de línea peligrosos
            st.markdown("".join(html_parts), unsafe_allow_html=True)
        else:
            st.info("Sin evidencias.")

with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
