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
# CSS RESPONSIVE (MÓVIL OK)
# ==========================================================
st.markdown("""
<style>
header, footer, [data-testid="stDecoration"] {
    display: none !important;
}

.titulo-smart {
    margin-left: 40px;
    margin-top: 10px;
    font-weight: bold;
    font-size: clamp(18px, 6vw, 26px);
}

/* ===== GALERÍA ===== */
.galeria {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
}

@media (max-width: 900px) {
    .galeria {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 600px) {
    .galeria {
        grid-template-columns: repeat(2, 1fr);
    }
}

.galeria img {
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    border-radius: 8px;
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
    if not valor:
        return None
    if isinstance(valor, list) and valor and isinstance(valor[0], dict):
        return valor[0].get("url")

    val = str(valor).strip()
    if val.lower() in ("", "none", "nan", "[]"):
        return None
    if val.startswith("http"):
        return val

    urls = re.findall(r'(https?://[^\s\)]+)', val)
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

    df["url_limpia"] = df["Foto"].apply(obtener_url_final) if "Foto" in df.columns else None

    with st.sidebar:
        st.header("⚙️ Config")
        usuarios = sorted(df["Usuario"].dropna().unique())
        sel_usuarios = st.multiselect("Repartidores", usuarios, default=usuarios)
        tipo_mapa = st.radio("Capa", ["Calle", "Satélite"])
        if st.button("🔄 Actualizar"):
            st.rerun()

    if not sel_usuarios:
        st.stop()

    df_f = df[df["Usuario"].isin(sel_usuarios)]

    # ---------------- MAPA ----------------
    m = folium.Map(
        location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()],
        zoom_start=15,
        zoom_control=False
    )

    if tipo_mapa == "Satélite":
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri"
        ).add_to(m)

    for usuario in sel_usuarios:
        u = df_f[df_f["Usuario"] == usuario]
        coords = u[["Latitud", "Longitud"]].values.tolist()
        if len(coords) > 1:
            folium.PolyLine(coords, weight=4).add_to(m)

        for _, r in u.iterrows():
            if r["url_limpia"]:
                folium.Marker(
                    [r["Latitud"], r["Longitud"]],
                    popup=folium.Popup(
                        f'<img src="{r["url_limpia"]}" width="180">',
                        max_width=180
                    )
                ).add_to(m)

    st_folium(m, height=420, width="100%", returned_objects=[])

    # ======================================================
    # GALERÍA + VISTA AMPLIADA (ESTABLE)
    # ======================================================
    st.markdown("### 📸 Evidencias")

    df_gal = df_f[df_f["url_limpia"].notna()]

    if not df_gal.empty:

        # ---- GALERÍA ----
        html = '<div class="galeria">'
        for _, row in df_gal.iterrows():
            html += f'<img src="{row["url_limpia"]}">'
        html += '</div>'

        st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")

        # ---- VISTA GRANDE ----
        with st.expander("🔍 Ver imágenes en grande"):
            for _, row in df_gal.iterrows():
                st.image(
                    row["url_limpia"],
                    caption=f"{row['Usuario']} · {row['Hora']}",
                    use_container_width=True
                )

# ==========================================================
# TAB CIERRE
# ==========================================================
with tab2:
    st.header("Cierre")
    if st.button("🚀 Archivar Día", type="primary"):
        st.success("Completado")
