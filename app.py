import streamlit as st
import pandas as pd
from pyairtable import Api
import cloudinary
import json
import folium
import math
import re
from streamlit_folium import st_folium
from folium.plugins import PolyLineTextPath

# ==========================================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================================
st.set_page_config(page_title="Monitor Reparto", layout="wide")

# ==========================================================
# CSS RESPONSIVE PARA GALERÍA (MÓVIL FRIENDLY)
# ==========================================================
st.markdown("""
<style>
header, footer, [data-testid="stDecoration"] {display:none;}

.titulo-smart {
    font-size: clamp(18px, 6vw, 26px);
    font-weight: bold;
    margin: 10px 0 10px 10px;
}

/* GALERÍA RESPONSIVA */
.galeria {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
}

/* TABLET / MÓVIL */
@media (max-width: 900px) {
    .galeria {
        grid-template-columns: repeat(2, 1fr);
    }
}

.galeria a {
    text-decoration: none;
}

.galeria img {
    width: 100%;
    height: 180px;
    object-fit: contain;       /* 🔑 NO recorta */
    background: #f2f2f2;
    border-radius: 8px;
    cursor: zoom-in;
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

    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# ==========================================================
# FUNCIONES
# ==========================================================
def obtener_url_final(valor):
    if not valor:
        return None
    if isinstance(valor, list) and len(valor) > 0:
        return valor[0].get("url")
    val = str(valor)
    if val.startswith("http"):
        return val
    urls = re.findall(r'(https?://[^\s\)]+)', val)
    return urls[0] if urls else None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

# ==========================================================
# UI
# ==========================================================
st.markdown('<div class="titulo-smart">🗞️ Monitor Reparto</div>', unsafe_allow_html=True)

records = table.all()
if not records:
    st.warning("Sin datos")
    st.stop()

df = pd.DataFrame([r["fields"] for r in records])
df.columns = [c.lower() for c in df.columns]

# Normalización
rename = {}
for c in df.columns:
    if "lat" in c: rename[c] = "Latitud"
    if "lon" in c: rename[c] = "Longitud"
    if "usu" in c: rename[c] = "Usuario"
    if "hora" in c: rename[c] = "Hora"
    if "foto" in c: rename[c] = "Foto"

df = df.rename(columns=rename)

df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
df = df.dropna(subset=["Latitud", "Longitud"])

df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
df = df.sort_values("Hora_dt")

df["url_limpia"] = df["Foto"].apply(obtener_url_final) if "Foto" in df.columns else None

with st.sidebar:
    st.header("⚙️ Configuración")
    usuarios = sorted(df["Usuario"].unique())
    sel = st.multiselect("Repartidores", usuarios, default=usuarios)

df_f = df[df["Usuario"].isin(sel)]

# ==========================================================
# MAPA
# ==========================================================
if not df_f.empty:
    m = folium.Map(location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()], zoom_start=15)

    for usuario in sel:
        u = df_f[df_f["Usuario"] == usuario]
        coords = u[["Latitud", "Longitud"]].values.tolist()

        if len(coords) > 1:
            folium.PolyLine(coords, weight=4).add_to(m)

        for _, r in u.iterrows():
            folium.Marker(
                [r["Latitud"], r["Longitud"]],
                popup=r["Hora"]
            ).add_to(m)

    st_folium(m, height=350, returned_objects=[])

# ==========================================================
# GALERÍA
# ==========================================================
st.markdown("### 📸 Evidencias")

df_gal = df_f[df_f["url_limpia"].notna()]

if not df_gal.empty:
    html = '<div class="galeria">'
    for _, r in df_gal.iterrows():
        html += f'''
        <a href="{r["url_limpia"]}" target="_blank">
            <img src="{r["url_limpia"]}">
        </a>
        '''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("🔍 Ver imágenes en grande"):
        for _, r in df_gal.iterrows():
            st.image(
                r["url_limpia"],
                caption=f"{r['Usuario']} · {r['Hora']}",
                use_container_width=True
            )
