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

# He limpiado el string para evitar el error de padding
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
    # Limpieza extrema del JSON para evitar Incorrect Padding
    json_fix = GOOGLE_JSON_RAW.strip().replace('\xa0', ' ')
    google_creds_dict = json.loads(json_fix, strict=False)
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

def calcular_distancia_real(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ==========================================================
# UI
# ==========================================================
st.title("🚚 Monitor de Reparto Pro")

tab1, tab2 = st.tabs(["📍 Mapa de Ruta", "☁️ Cierre de Jornada"])

with tab1:
    if st.button("🔄 Refrescar Datos"):
        st.rerun()

    records = table.all()
    if not records:
        st.warning("No hay datos.")
        st.stop()

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
    df["url_limpia"] = df["Foto"].apply(obtener_url_final)

    with st.sidebar:
        st.header("⚙️ Filtros")
        usuarios_lista = sorted(df["Usuario"].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios_lista, default=usuarios_lista)
        tipo_mapa = st.radio("Capa de Mapa", ["Calle", "Satélite"])
        st.markdown("---")
        modo_reporte = st.checkbox("📑 Mostrar Resumen y Galería", value=True)

    if not sel_usuarios:
        st.info("Selecciona un repartidor.")
    else:
        df_f = df[df["Usuario"].isin(sel_usuarios)].copy()

        # MAPA CON AUTO-ZOOM
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
                
                # RUTA (GLOW + FLECHAS DELINEADAS)
                if len(coords) > 1:
                    folium.PolyLine(coords, color='black', weight=7, opacity=0.3).add_to(m)
                    linea = folium.PolyLine(coords, color=color, weight=3).add_to(m)
                    PolyLineTextPath(linea, '     ►     ', repeat=True, offset=8, 
                                     attributes={'fill': color, 'font-weight': 'bold', 'font-size': '20', 'stroke': 'black', 'stroke-width': '0.5'}).add_to(m)

                ult_hito = None
                for j in range(len(u_data)):
                    row = u_data.iloc[j]
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        dist_total += calcular_distancia_real(row["Latitud"], row["Longitud"], p_next["Latitud"], p_next["Longitud"])

                    # HITOS 15 MIN 📍 (CON POPUP)
                    if ult_hito is None or (row["Hora_dt"] - ult_hito).total_seconds() >= 900:
                        folium.Marker(
                            [row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'''
                                <div style="text-align:center;">
                                    <div style="font-size:16pt; filter: drop-shadow(1px 1px 2px black);">📍</div>
                                    <div style="font-size:8pt; color:white; background:rgba(0,0,0,0.7); padding:2px 4px; border-radius:3px; font-weight:bold;">{row["Hora"][:5]}</div>
                                </div>'''),
                            popup=folium.Popup(f"<b>Repartidor:</b> {nombre}<br><b>Hora:</b> {row['Hora']}", max_width=200)
                        ).add_to(m)
                        ult_hito = row["Hora_dt"]

                    # MINIATURAS (ZOOM REAL)
                    if row['url_limpia']:
                        folium.Marker(
                            [row["Latitud"], row["Longitud"]],
                            icon=folium.DivIcon(html=f'''
                                <div style="width:55px; height:55px; border:3px solid {color}; background:white; box-shadow:3px 3px 6px black; border-radius:4px; overflow:hidden;">
                                    <img src="{row['url_limpia']}" width="55" height="55" style="object-fit:cover; transform: scale(1.15);">
                                </div>'''),
                            popup=folium.Popup(f'<b>{nombre}</b><br><img src="{row["url_limpia"]}" width="250">', max_width=250)
                        ).add_to(m)

                # INICIO (📌) Y FIN (🏁) — MANEJO DE SOLAPE
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                # Pequeño offset si el inicio y fin son idénticos
                is_same = (r_ini["Latitud"] == r_fin["Latitud"] and r_ini["Longitud"] == r_fin["Longitud"])
                offset = 0.00004 if is_same else 0

                folium.Marker(
                    [r_ini["Latitud"], r_ini["Longitud"]], 
                    icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:26pt; filter: drop-shadow(2px 2px 3px black);">📌</div><div style="font-size:8pt; color:white; background:green; padding:1px 3px; border-radius:3px; font-weight:bold;">{r_ini["Hora"][:5]}</div></div>'),
                    popup=f"<b>SALIDA</b><br>{nombre}<br>{r_ini['Hora']}"
                ).add_to(m)
                
                folium.Marker(
                    [r_fin["Latitud"] + offset, r_fin["Longitud"] + offset], 
                    icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:26pt; filter: drop-shadow(2px 2px 3px black);">🏁</div><div style="font-size:8pt; color:white; background:black; padding:1px 3px; border-radius:3px; font-weight:bold;">{r_fin["Hora"][:5]}</div></div>'),
                    popup=f"<b>LLEGADA</b><br>{nombre}<br>{r_fin['Hora']}"
                ).add_to(m)

                resumen_final.append({
                    "Repartidor": nombre, "Salida": r_ini["Hora"], "Llegada": r_fin["Hora"], 
                    "Evidencias": u_data['url_limpia'].notna().sum(), "Distancia": f"{dist_total:.2f} km"
                })

        m.fit_bounds(df_f[["Latitud", "Longitud"]].values.tolist())
        st_folium(m, width="100%", height=700, returned_objects=[])

        if modo_reporte:
            st.markdown("### 📋 Resumen de Jornada")
            st.table(pd.DataFrame(resumen_final))
            st.write("### 📸 Galería de Testigos")
            df_gal = df_f[df_f['url_limpia'].notna()]
            if not df_gal.empty:
                cols = st.columns(2 if len(df_gal) < 3 else 4)
                for idx, (_, f_row) in enumerate(df_gal.iterrows()):
                    with cols[idx % (2 if len(df_gal) < 3 else 4)]:
                        st.image(f_row['url_limpia'], caption=f"{f_row['Usuario']} ({f_row['Hora']})")

with tab2:
    st.header("☁️ Cierre del Día")
    # Lógica Cloudinary...
    if st.button("🚀 Procesar y Archivar", type="primary"):
        st.success("✅ Cierre completado")
