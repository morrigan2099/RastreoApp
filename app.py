import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
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
# CSS MAESTRO (Imágenes ajustadas + Sidebar visible)
# ==========================================================
st.markdown("""
<style>
/* 1. LIMPIEZA DE INTERFAZ (Pero dejando el botón del sidebar vivo) */
header[data-testid="stHeader"] {
    background: transparent !important;
}
/* Esto oculta la decoración roja de arriba pero deja el botón clicable */
[data-testid="stDecoration"] { display: none !important; }
footer { display: none !important; }

/* 2. TÍTULO ADAPTABLE */
.titulo-smart {
    margin-left: 50px; /* Espacio para no chocar con el botón del menú */
    margin-top: 15px;
    font-weight: bold;
    font-size: clamp(18px, 6vw, 26px);
    color: var(--text-color);
}

/* 3. GALERÍA GRID RESPONSIVA */
.galeria-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr); /* Escritorio: 4 columnas */
    gap: 10px;
    padding: 10px 0;
}

/* REGLA MÓVIL: 2 COLUMNAS */
@media (max-width: 768px) {
    .galeria-container {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* 4. ESTILO DE LA FOTO (SIN RECORTES) */
.foto-card {
    background-color: #f0f2f6; /* Fondo gris para rellenar */
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    overflow: hidden;
    position: relative;
    /* Esto hace que el contenedor sea siempre cuadrado */
    padding-top: 100%; 
    width: 100%;
}

.foto-card img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    /* AQUÍ LA MAGIA: contain muestra la foto entera sin recortar */
    object-fit: contain; 
}

.foto-caption {
    font-size: 11px;
    text-align: center;
    padding: 4px;
    color: #333;
    font-weight: bold;
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

    cloudinary.config(
        cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key=st.secrets["CLOUDINARY_API_KEY"],
        api_secret=st.secrets["CLOUDINARY_API_SECRET"]
    )

    g_creds = dict(st.secrets["google_creds"])
    g_creds["private_key"] = g_creds["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        g_creds,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    gc = gspread.authorize(creds)

    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# ==========================================================
# FUNCIONES
# ==========================================================
def obtener_url_final(valor):
    if not valor: return None
    # Prioridad: Lista de Airtable
    if isinstance(valor, list) and len(valor) > 0 and isinstance(valor[0], dict):
        return valor[0].get("url")
    
    val_str = str(valor).strip()
    if val_str.lower() in ("", "none", "nan", "[]"): return None
    if val_str.startswith("http"): return val_str
    
    urls = re.findall(r'(https?://[^\s\)]+)', val_str)
    return urls[0] if urls else None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# UI
# ==========================================================
st.markdown('<div class="titulo-smart">🗞️ Monitor Reparto Folletos</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📍 Mapa", "☁️ Cierre"])

# ==========================================================
# TAB MAPA
# ==========================================================
with tab1:
    records = table.all()
    if not records:
        st.warning("Sin datos")
        st.stop()

    df = pd.DataFrame([r["fields"] for r in records])
    df.columns = [c.lower() for c in df.columns]

    rename = {
        c: "Latitud" if "lat" in c else
           "Longitud" if "lon" in c else
           "Usuario" if "usu" in c else
           "Hora" if "hora" in c else
           "Foto" if "foto" in c and "etiq" not in c else c
        for c in df.columns
    }
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

    with st.sidebar:
        st.header("⚙️ Config")
        # Botón cerrar sidebar nativo
        usuarios = sorted(df["Usuario"].dropna().unique())
        sel_usuarios = st.multiselect("Repartidores", usuarios, default=usuarios)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"):
            st.rerun()

    if not sel_usuarios:
        st.stop()

    df_f = df[df["Usuario"].isin(sel_usuarios)]

    # ---------------- CÁLCULO DE ESTADÍSTICAS ----------------
    stats_data = []
    
    # Mapa Base
    m = folium.Map(
        location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()],
        zoom_start=15, zoom_control=False
    )
    
    if tipo_mapa == "Satélite":
        folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri").add_to(m)

    colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']

    for i, usuario in enumerate(sel_usuarios):
        color = colores[i % len(colores)]
        u_data = df_f[df_f["Usuario"] == usuario].reset_index(drop=True)
        
        if u_data.empty: continue
        
        # Calcular Distancia Total
        dist_total = 0.0
        coords = u_data[["Latitud", "Longitud"]].values.tolist()
        
        if len(coords) > 1:
            linea = folium.PolyLine(coords, color=color, weight=4, opacity=0.8).add_to(m)
            PolyLineTextPath(linea, '   ►   ', repeat=True, offset=8, attributes={'fill': color, 'font-size': '18'}).add_to(m)
            
            # Sumar distancias
            for k in range(len(coords) - 1):
                dist_total += calcular_distancia(coords[k][0], coords[k][1], coords[k+1][0], coords[k+1][1])

        # Pines del Mapa
        ult_hito = None
        for _, r in u_data.iterrows():
            # 15 mins
            if ult_hito is None or (r["Hora_dt"] - ult_hito).total_seconds() >= 900:
                folium.Marker([r["Latitud"], r["Longitud"]], 
                              icon=folium.DivIcon(html='<div style="font-size:18pt;">📍</div>'),
                              popup=f"{usuario}<br>{r['Hora']}").add_to(m)
                ult_hito = r["Hora_dt"]
            
            # Foto Mini
            if r["url_limpia"]:
                folium.Marker([r["Latitud"], r["Longitud"]],
                    icon=folium.DivIcon(html=f'<div style="width:40px; height:40px; border:2px solid {color}; border-radius:4px; overflow:hidden;"><img src="{r["url_limpia"]}" style="width:100%; height:100%; object-fit:cover;"></div>'),
                    popup=folium.Popup(f'<img src="{r["url_limpia"]}" width="150">', max_width=150)).add_to(m)

        # Inicio / Fin
        r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
        off = 0.00009 if (abs(r_ini["Latitud"] - r_fin["Latitud"]) < 0.00005) else 0
        folium.Marker([r_ini["Latitud"], r_ini["Longitud"]], icon=folium.DivIcon(html='<div style="font-size:22pt;">📌</div>'), popup=f"Inicio: {r_ini['Hora']}").add_to(m)
        folium.Marker([r_fin["Latitud"]+off, r_fin["Longitud"]+off], icon=folium.DivIcon(html='<div style="font-size:22pt;">🏁</div>'), popup=f"Fin: {r_fin['Hora']}").add_to(m)

        # Agregar a Estadísticas
        stats_data.append({
            "Repartidor": usuario,
            "Fotos": u_data['url_limpia'].notna().sum(),
            "Distancia": f"{dist_total:.2f} km"
        })

    st_folium(m, height=400, width="100%", returned_objects=[])

    # ======================================================
    # ESTADÍSTICAS POR USUARIO
    # ======================================================
    st.markdown("### 📊 Estadísticas")
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

    # ======================================================
    # GALERÍA MEJORADA (HTML GRID + CONTAIN)
    # ======================================================
    st.markdown("### 📸 Evidencias")

    df_gal = df_f[df_f["url_limpia"].notna()]

    if not df_gal.empty:
        html = '<div class="galeria-container">'
        for _, row in df_gal.iterrows():
            nombre_corto = row["Usuario"].split()[0]
            # Link abre imagen completa en pestaña nueva
            html += f'''
            <div>
                <a href="{row["url_limpia"]}" target="_blank" style="text-decoration:none;">
                    <div class="foto-card">
                        <img src="{row["url_limpia"]}">
                    </div>
                    <div class="foto-caption">{nombre_corto} {row["Hora"][:5]}</div>
                </a>
            </div>
            '''
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("No hay evidencias fotográficas.")

# ==========================================================
# TAB CIERRE
# ==========================================================
with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
