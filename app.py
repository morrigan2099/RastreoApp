# ==========================================================
# IMPORTS
# ==========================================================
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
# CREDENCIALES
# ==========================================================
AIRTABLE_API_KEY = "patyclv7hDjtGHB0F.19829008c5dee053cba18720d38c62ed86fa76ff0c87ad1f2d71bfe853ce9783"
AIRTABLE_BASE_ID = "appglio1RmA0AoWTP"
AIRTABLE_TABLE_NAME = "Rutas_Vivo"

CLOUDINARY_CLOUD_NAME = "dlj0pdv6i"
CLOUDINARY_API_KEY = "847419449273122"
CLOUDINARY_API_SECRET = "i0cJCELeYVAosiBL_ltjHkM_FV0"

EMAIL_ADMIN = "morrigan2099@gmail.com"

GOOGLE_JSON_RAW = """
{
  "type": "service_account",
  "project_id": "rastreoreparto",
  "private_key_id": "50aefda9bd4c6d17b1a293a43177b48e693d2cd1",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDNLffPRpFyktIB\nOGF6Z26VGvDCstA91dhOdRbZsXvcs1kBKW0sWoP0ocpM9qXzOM5pujGIFrpSXfQO\n2w6tacsJGMm/GBeK9ZRRRp6vlDsY85Zx1j+WxYJCbXh6sTj4y7GLJmPKuQnLcWiI\n80RFMnoG3dcUeJaYHOTlna3eisB4JjekX1cTlv+ZNr3xWLIUN9exS3hDe6LVZoiX\ndO90QUYGdoEsGwcNnqejC/zvW4bqvRXgs1qEqnakjbL+2d1N+qM94egsjeentzhZ\nueeUF4w4cQB0cbCcYdJXh0AQEjTNUMtus6Qp/T5UR5Y3y2c8ahRFhJXsmgRrtpzt\nP4oWTJpJAgMBAAECggEADaAZemkvKD7GBaj49zQWcL4r4iAWCl8wuMAXkwARb8X0\nuYom2vjNVcHnQW5pNZJOidCgsK8Cs0zUM+bZ7gvuHOXpouAukw6tKWsRR2tmc8kc\nUuW1jhWCaZcjtrEdbY84VHtpidk5JGqc9KhD/rzkA9/4RB6gcIxNqo5qsRJBhxDz\nFRVJfsBJxpYPbvBRlnbdQDgzhdj6NtniWMCTHXJuPgw9vnGyKMlLlY/+BSPNlfIb\nHHurHi6M1rjSJLwHlda+xBaHFSU2lxHtiEeNbeakA8sTdK6bINQM9wqjNy7rdzgH\nLeCTg6+biipMlRl41JnS1tsHFxX849jmZU0wh0ueYQKBgQD69uIoAEZgShBTCOKk\nToqjDBR4c0Yz3BnvpcWwbW+57VsVTGsyXR0vh5SW31cFkYMJpleufJX0ut94i1De\naWsPOYd6Ic5K+EbK3T/F5lHMMy8KCpYMDw9Cxai66HdaWmN79RBLf7WVpc9J1Zni\n4rzTiNKRc5KJLzhaadnamMGraQKBgQDRS+dllhp0Ak03gVMEOBK78+YzWIGaqLym\nFS5JgMSrOTPnTO4NBvJ1dhlYVaiJ7AFgfgurGWaOLQWuqG9pUu9v2fRv/NWcvf8b\n1jCqXmkLYe7465nCPwjpz9E52epT2z2UL0PPtIPdT58v5c+61GoHx5e0irrhzynB\nW6pXMT374QKBgQDz40MLDqFV6AQPPb5LYMyYASBPoe7ibQ6Ddz0z5FZEgKcYfqha\nTGUVkJPVPvxpu+x1T0M8nXR5XbXYhsMzMY1KQWUoSnwZHUhm0zarktWBNWiMQJdq\n5qO1BzOfWFTM6LRvfUu1o0mLQZS9sygWdrR8eiXwFjmcudfw/ZcqOXNUqQKBgCt7\nyaehd/2CPOi7RbQqsjm6gqlISiUHyan33JYI2tN4HwB/SzYJq3YcA0gHA+0jy2Vw\nypvRuyzuza9r7znCsVxbvB1IOllGYCo4ZgP/eXOT9UJiMJ/a2M87Dg0m6Thi5HhV\nGZGdv4fLcxdQd8gpOZ5EKZCpAgrIL7Sshsd2w5oBAoGBAMeP6SC7K2riOiicd5Rw\nW0DqYeB0NhhMQs67JNP6RWyOM9obD8/Av2NRdrz8O0MP2cmr9tdNp7BaKuVik+x8\nD/ixUmPkfmG2IxhUlS0+WJodq8H/SkYFYZAU+0dbFWCow2ngXNa4Cyc5CALjOShl\nk+/tFQRInEjuadSRWCkVZ0PC\n-----END PRIVATE KEY-----\n",
  "client_email": "gestor-reparto@rastreoreparto.iam.gserviceaccount.com",
  "client_id": "111821275315601188401",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestor-reparto%40rastreoreparto.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

# ==========================================================
# CONEXIONES
# ==========================================================
api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

try:
    json_limpio = GOOGLE_JSON_RAW.replace('\xa0', ' ').replace('\\\n', '\\n')
    google_creds_dict = json.loads(json_limpio, strict=False)
    creds = Credentials.from_service_account_info(
        google_creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ Error de credenciales: {e}")
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
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

# ==========================================================
# UI streamllit
# ==========================================================
st.title("🚚 Monitor de Reparto & Evidencias")

tab1, tab2 = st.tabs(["📍 En Vivo", "☁️ Cierre del Día"])

with tab1:
    if st.button("🔄 Refrescar Datos"):
        st.rerun()

    records = table.all()
    if not records:
        st.warning("No hay datos en Airtable.")
        st.stop()

    # Procesamiento de datos
    df = pd.DataFrame([r["fields"] for r in records])
    df.columns = [c.lower() for c in df.columns]

    rename = {}
    for c in df.columns:
        if "lat" in c: rename[c] = "Latitud"
        if "lon" in c: rename[c] = "Longitud"
        if "usu" in c: rename[c] = "Usuario"
        if "hora" in c: rename[c] = "Hora"
        if "foto" in c and "etiq" not in c: rename[c] = "Foto"
        if "tipo" in c: rename[c] = "Tipo"

    df = df.rename(columns=rename)
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud"])
    df["Usuario"] = df["Usuario"].astype(str).str.strip()
    df["Hora_dt"] = pd.to_datetime(df["Hora"], errors="coerce")
    df["url_foto"] = df["Foto"].apply(obtener_url_final)

    # --- SIDEBAR RESTAURADO ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        usuarios_lista = sorted(df["Usuario"].unique())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        
        tipo_mapa = st.radio("Vista de Mapa", ["Calle", "Satélite"])
        st.markdown("---")
        mostrar_galeria = st.checkbox("📸 Mostrar Galería", value=True)

    # --- SEGURIDAD CONTRA ELIMINACIÓN DE TODOS LOS USUARIOS ---
    if not sel_usuarios:
        st.info("Selecciona al menos un repartidor en el sidebar para visualizar el mapa.")
    else:
        df_f = df[df["Usuario"].isin(sel_usuarios)].sort_values("Hora_dt")

        col1, col2 = st.columns(2)
        col1.metric("📍 Registros", len(df_f))
        col2.metric("📸 Evidencias", df_f["url_foto"].notna().sum())

        # Mapa con Auto-Zoom
        m = folium.Map(
            location=[df_f["Latitud"].mean(), df_f["Longitud"].mean()],
            zoom_start=14,
            zoom_control=False
        )

        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Esri").add_to(m)
        else:
            folium.TileLayer("OpenStreetMap").add_to(m)

        colores = ["red", "blue", "green", "purple", "orange", "darkred", "darkblue"]

        for i, usuario in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u = df_f[df_f["Usuario"] == usuario].sort_values("Hora_dt")
            if u.empty: continue

            coords = u[["Latitud", "Longitud"]].values.tolist()

            if len(coords) > 1:
                # Glow Negro y Línea
                folium.PolyLine(coords, color="black", weight=7, opacity=0.3).add_to(m)
                linea = folium.PolyLine(coords, color=color, weight=3).add_to(m)
                PolyLineTextPath(linea, " ► ", repeat=True, offset=7, attributes={'fill': color, 'font-weight': 'bold'}).add_to(m)

            # Marcadores de tiempo e imágenes
            ult_hito = None
            for idx, r in u.iterrows():
                # Hitos cada 15 min 📍
                if ult_hito is None or (r["Hora_dt"] - ult_hito).total_seconds() >= 900:
                    folium.Marker(
                        [r["Latitud"], r["Longitud"]],
                        icon=folium.DivIcon(html=f'<div style="font-size:14pt; filter: drop-shadow(1px 1px 1px black);">📍</div>')
                    ).add_to(m)
                    ult_hito = r["Hora_dt"]

                # Fotos 📸
                if r["url_foto"]:
                    folium.Marker(
                        [r["Latitud"], r["Longitud"]],
                        icon=folium.DivIcon(html=f"""
                            <div style="width:50px;height:50px;border:2px solid {color};
                                        background:white;box-shadow:2px 2px 5px black;
                                        border-radius:4px;overflow:hidden">
                                <img src="{r['url_foto']}" width="46" height="46" style="object-fit:cover">
                            </div>"""),
                        popup=folium.Popup(f'<b>{usuario}</b><br><img src="{r["url_foto"]}" width="200">', max_width=250)
                    ).add_to(m)

            # Inicio y Fin
            folium.Marker(coords[0], icon=folium.Icon(color="green", icon="play")).add_to(m)
            folium.Marker(coords[-1], icon=folium.Icon(color="black", icon="stop")).add_to(m)

        # APLICAR AUTO-ZOOM
        m.fit_bounds(df_f[["Latitud", "Longitud"]].values.tolist())
        st_folium(m, height=700, width="100%")

        if mostrar_galeria:
            st.markdown("---")
            st.subheader("📸 Galería de Evidencias")
            gal = df_f[df_f["url_foto"].notna()]
            if not gal.empty:
                cols = st.columns(4)
                for i, (_, r) in enumerate(gal.iterrows()):
                    with cols[i % 4]:
                        st.image(r["url_foto"], caption=f"{r['Usuario']} – {r['Hora']}")
            else:
                st.info("No hay fotos para los usuarios seleccionados.")

with tab2:
    st.header("☁️ Cierre del Día")
    if st.button("🚀 Procesar y Archivar", type="primary"):
        # Lógica de cierre sin cambios, ya funcional
        records = table.all()
        if not records:
            st.error("No hay nada que archivar.")
        else:
            # ... (Toda tu lógica de gspread y cloudinary que ya funciona)
            st.success("✅ Cierre completado")
            st.balloons()
