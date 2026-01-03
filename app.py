import streamlit as st
import pandas as pd
from pyairtable import Api
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import json
import folium
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor de Reparto Pro", layout="wide")

# ==========================================
# 🔐 ZONA DE CONFIGURACIÓN
# ==========================================

# 1. AIRTABLE (Genera uno nuevo por seguridad)
AIRTABLE_API_KEY = "patyclv7hDjtGHB0F.19829008c5dee053cba18720d38c62ed86fa76ff0c87ad1f2d71bfe853ce9783"
AIRTABLE_BASE_ID = "appglio1RmA0AoWTP"
AIRTABLE_TABLE_NAME = "Rutas_Vivo"

# 2. CLOUDINARY (Genera uno nuevo por seguridad)
CLOUDINARY_CLOUD_NAME = "dlj0pdv6i"
CLOUDINARY_API_KEY = "847419449273122"
CLOUDINARY_API_SECRET = "i0cJCELeYVAosiBL_ltjHkM_FV0" 

# 3. GOOGLE SHEETS
# Instrucción: Pega el JSON nuevo. El código limpiará los errores de formato automático.
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

# 4. ADMIN
EMAIL_ADMIN = "morrigan2099@gmail.com"

# ==========================================
# 🔌 CONEXIÓN A SERVICIOS
# ==========================================
try:
    if "REEMPLAZA" in GOOGLE_JSON_RAW or len(GOOGLE_JSON_RAW) < 50:
        st.error("⚠️ Falta pegar el JSON de Google en la variable GOOGLE_JSON_RAW.")
        st.stop()
        
    json_limpio = GOOGLE_JSON_RAW.replace('\xa0', ' ').replace('\\\n', '\\n')
    
    google_creds_dict = json.loads(json_limpio, strict=False)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)

    api = Api(AIRTABLE_API_KEY)
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
    
    cloudinary.config( 
        cloud_name = CLOUDINARY_CLOUD_NAME, 
        api_key = CLOUDINARY_API_KEY, 
        api_secret = CLOUDINARY_API_SECRET,
        secure = True
    )

except json.JSONDecodeError as e:
    st.error(f"Error de formato JSON: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error de conexión general: {e}")
    st.stop()

# ==========================================
# 📱 INTERFAZ DE USUARIO
# ==========================================

st.title("🚚 Monitor de Reparto & Cloudinary")

tab1, tab2 = st.tabs(["📍 En Vivo (Mapa Dinámico)", "☁️ Procesar y Archivar"])

# ------------------------------------------
# PESTAÑA 1: MAPA DINÁMICO + RUTA
# ------------------------------------------
with tab1:
    col_kpi, col_btn = st.columns([4,1])
    with col_btn:
        if st.button("🔄 Refrescar"):
            st.rerun()

    try:
        records = table.all()
    except Exception as e:
        st.error(f"Error leyendo Airtable: {e}")
        records = []

    if records:
        data = [r['fields'] for r in records]
        df = pd.DataFrame(data)
        
        # --- NORMALIZACIÓN DE NOMBRES ---
        df.columns = [c.lower() for c in df.columns]
        
        rename_map = {}
        for col in df.columns:
            if 'lat' in col: rename_map[col] = 'Latitud'
            if 'lon' in col: rename_map[col] = 'Longitud'
            if 'usu' in col: rename_map[col] = 'Usuario'
            if 'tipo' in col: rename_map[col] = 'Tipo'
            if 'foto' in col and 'etiq' not in col: rename_map[col] = 'Foto'
            if 'etiq' in col: rename_map[col] = 'Etiqueta_Foto'
            if 'fecha' in col: rename_map[col] = 'Fecha'
            if 'hora' in col: rename_map[col] = 'Hora'
            if 'zona' in col: rename_map[col] = 'Zona'
            
        df = df.rename(columns=rename_map)

        if 'Tipo' not in df.columns: df['Tipo'] = 'GPS'

        df_gps = df[df['Tipo'] != 'FOTO'].copy()
        df_fotos = df[df['Tipo'] == 'FOTO'].copy()
        
        st.metric("📦 Paquetes/Evidencias hoy", len(df_fotos))
        
import math
import pandas as pd
import streamlit as st
import folium
import ast
import re
from streamlit_folium import st_folium
from folium.plugins import PolyLineTextPath

# --- 1. EXTRACCIÓN DE URL (Soporta el formato de texto con paréntesis) ---
def obtener_url_final(valor):
    if not valor or str(valor).lower() in ['nan', 'none', '', '[]']:
        return None
    val_str = str(valor).strip()
    # Extraer link de entre los paréntesis si existe
    if '(' in val_str and ')' in val_str:
        urls = re.findall(r'\((https?://[^\)]+)\)', val_str)
        if urls: return urls[0]
    # Caso URL directa
    if val_str.startswith('http'): return val_str
    return None

# --- 2. DISTANCIA REAL ---
def calcular_distancia_real(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# --- SECCIÓN 4: MAPA INTEGRAL ---
if not df_gps.empty:
    st.markdown("---")
    
    # Nombres de columnas según tu tabla
    c_lat, c_lon = "Latitud", "Longitud"
    c_user, c_hora = "Usuario", "Hora"
    c_foto, c_etiqueta = "Foto", "Etiqueta_Foto"

    # Preparación de datos
    df_gps[c_lat] = pd.to_numeric(df_gps[c_lat], errors='coerce')
    df_gps[c_lon] = pd.to_numeric(df_gps[c_lon], errors='coerce')
    df_gps = df_gps.dropna(subset=[c_lat, c_lon])
    
    # Pre-limpieza de fotos (Agnóstico al 'Tipo')
    df_gps['url_limpia'] = df_gps[c_foto].apply(obtener_url_final)
    
    if c_hora in df_gps.columns:
        df_gps['hora_dt'] = pd.to_datetime(df_gps[c_hora], format='%H:%M:%S', errors='coerce')
        df_gps = df_gps.sort_values(by=[c_user, 'hora_dt'])

    with st.sidebar:
        st.header("⚙️ Configuración")
        tipo_mapa = st.radio("Vista", ["Calle", "Satélite"])
        modo_reporte = st.checkbox("📑 Activar Modo Reporte", value=True)
        usuarios = sorted(df_gps[c_user].unique().tolist())
        sel_usuarios = st.multiselect("Repartidores", usuarios, default=usuarios)

    df_f = df_gps[df_gps[c_user].isin(sel_usuarios)].copy()

    if not df_f.empty:
        # Mapa centrado
        m = folium.Map(location=[df_f[c_lat].mean(), df_f[c_lon].mean()], zoom_start=15, zoom_control=False)
        
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
        else:
            folium.TileLayer('OpenStreetMap').add_to(m)

        colores = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00']
        resumen_final = []

        for i, nombre in enumerate(sel_usuarios):
            color = colores[i % len(colores)]
            u_data = df_f[df_f[c_user] == nombre].reset_index(drop=True)
            dist_total = 0.0
            
            if not u_data.empty:
                # 1. RUTA TOTAL (Une todos los registros cronológicamente)
                coords_ruta = u_data[[c_lat, c_lon]].values.tolist()
                if len(coords_ruta) > 1:
                    # Glow Negro (Base)
                    folium.PolyLine(coords_ruta, color='black', weight=7, opacity=0.35).add_to(m)
                    # Línea de Color (Principal)
                    linea = folium.PolyLine(coords_ruta, color=color, weight=3).add_to(m)
                    # Flechas direccionales mínimas
                    PolyLineTextPath(linea, '                        ►                        ', repeat=True, offset=8, 
                                     attributes={'fill': color, 'font-weight': 'bold', 'font-size': '22', 'stroke': 'black', 'stroke-width': '0.7'}).add_to(m)

                # 2. PROCESAMIENTO DE HITOS
                ult_hito_t = None
                for j in range(len(u_data)):
                    row = u_data.iloc[j]
                    
                    # Cálculo de Distancia y Paradas 🚩
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        dist_total += calcular_distancia_real(row[c_lat], row[c_lon], p_next[c_lat], p_next[c_lon])
                        if (p_next['hora_dt'] - row['hora_dt']).total_seconds() / 60 >= 5:
                            folium.Marker([row[c_lat], row[c_lon]], icon=folium.DivIcon(html='<div style="font-size:20pt; filter: drop-shadow(2px 2px 2px black);">🚩</div>')).add_to(m)

                    # Pines cada 15 min 📍 con Sombra y Hora
                    if ult_hito_t is None or (row['hora_dt'] - ult_hito_t).total_seconds() >= 900:
                        folium.Marker([row[c_lat], row[c_lon]], icon=folium.DivIcon(html=f'''
                            <div style="text-align:center;">
                                <div style="font-size:18pt; filter: drop-shadow(1px 1px 2px black);">📍</div>
                                <div style="font-size:8pt; color:white; background:rgba(0,0,0,0.7); padding:2px 4px; border-radius:3px; font-weight:bold;">{row[c_hora][:5]}</div>
                            </div>''')).add_to(m)
                        ult_hito_t = row['hora_dt']

                    # 3. FOTOS (Miniaturas sobre la ruta)
                    # Si tiene URL (no importa el 'Tipo'), la ponemos
                    if row['url_limpia']:
                        folium.Marker(
                            [row[c_lat], row[c_lon]],
                            icon=folium.DivIcon(html=f'''
                                <div style="width:55px; height:55px; border:3px solid {color}; background:white; box-shadow:3px 3px 6px black; padding:2px; border-radius:4px;">
                                    <img src="{row['url_limpia']}" width="49" height="49" style="object-fit:cover; border-radius:2px;">
                                </div>'''),
                            popup=folium.Popup(f'<img src="{row["url_limpia"]}" width="280">', max_width=280)
                        ).add_to(m)

                # 4. INICIO Y FIN (📌 y 🏁 con Sombra y Popups de Hora)
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                folium.Marker([r_ini[c_lat], r_ini[c_lon]], icon=folium.DivIcon(html='<div style="font-size:28pt; filter: drop-shadow(2px 2px 3px black);">📌</div>'), popup=f"SALIDA: {r_ini[c_hora]}").add_to(m)
                folium.Marker([r_fin[c_lat]+0.00002, r_fin[c_lon]+0.00002], icon=folium.DivIcon(html='<div style="font-size:28pt; filter: drop-shadow(2px 2px 3px black);">🏁</div>'), popup=f"LLEGADA: {r_fin[c_hora]}").add_to(m)

                resumen_final.append({"Repartidor": nombre, "Salida": r_ini[c_hora], "Llegada": r_fin[c_hora], "KM": f"{dist_total:.2f} km"})

        m.fit_bounds(df_f[[c_lat, c_lon]].values.tolist())
        st_folium(m, width="100%", height=700, returned_objects=[])

        if modo_reporte:
            st.markdown("### 📋 Resumen de Jornada")
            st.table(pd.DataFrame(resumen_final))
            st.write("### 📸 Galería de Testigos")
            # Galería de cualquier fila que tenga foto
            df_galeria = df_f[df_f['url_limpia'].notna()]
            if not df_galeria.empty:
                cols_g = st.columns(4)
                for idx, (_, f_row) in enumerate(df_galeria.iterrows()):
                    with cols_g[idx % 4]:
                        st.image(f_row['url_limpia'], caption=f"{f_row[c_user]} - {f_row.get(c_etiqueta, 'Foto')} ({f_row[c_hora]})")
              
# ------------------------------------------
# PESTAÑA 2: MOTOR DE MIGRACIÓN
# ------------------------------------------
with tab2:
    st.header("🗃️ Cierre del Día: Migración a Cloudinary")
    
    if st.button("🚀 INICIAR PROCESAMIENTO Y ARCHIVADO", type="primary"):
        records = table.all()
        
        if not records:
            st.warning("No hay datos en Airtable.")
        else:
            bar = st.progress(0)
            status = st.status("Iniciando motor...", expanded=True)
            
            data = [r['fields'] for r in records]
            df = pd.DataFrame(data)
            
            # Normalización para guardado
            df.columns = [c.lower() for c in df.columns]
            rename_map_save = {}
            for col in df.columns:
                if 'fecha' in col: rename_map_save[col] = 'Fecha'
                if 'usu' in col: rename_map_save[col] = 'Usuario'
                if 'hora' in col: rename_map_save[col] = 'Hora'
                if 'tipo' in col: rename_map_save[col] = 'Tipo'
                if 'foto' in col and 'etiq' not in col: rename_map_save[col] = 'Foto'
                if 'etiq' in col: rename_map_save[col] = 'Etiqueta_Foto'
                if 'lat' in col: rename_map_save[col] = 'Latitud'
                if 'lon' in col: rename_map_save[col] = 'Longitud'
                if 'zona' in col: rename_map_save[col] = 'Zona'
            
            df = df.rename(columns=rename_map_save)

            fecha = df['Fecha'].iloc[0] if 'Fecha' in df.columns else "General"
            nombre_libro = f"Reparto_{fecha}"
            
            try:
                sh = gc.open(nombre_libro)
                status.write(f"📂 Libro encontrado: {nombre_libro}")
            except gspread.exceptions.SpreadsheetNotFound:
                sh = gc.create(nombre_libro)
                sh.share(EMAIL_ADMIN, perm_type='user', role='writer')
                status.write(f"✨ Libro CREADO: {nombre_libro}")
            
            if 'Usuario' in df.columns:
                usuarios = df['Usuario'].unique()
            else:
                usuarios = ["Desconocido"]

            total_pasos = len(records)
            pasos_completados = 0

            for usuario in usuarios:
                status.write(f"🔄 Procesando: **{usuario}**")
                
                if 'Usuario' in df.columns:
                    df_u = df[df['Usuario'] == usuario].copy()
                else:
                    df_u = df.copy()
                
                def procesar_imagen_cloudinary(row):
                    if row.get('Tipo') != 'FOTO' or 'Foto' not in row or not isinstance(row['Foto'], list):
                        return ""
                    try:
                        airtable_url = row['Foto'][0]['url']
                        nombre_archivo = f"{fecha}_{usuario}_{str(row.get('Hora','')).replace(':','')}"
                        
                        res = cloudinary.uploader.upload(
                            airtable_url, 
                            public_id=nombre_archivo,
                            folder="repartos_evidencia",
                            format="webp"
                        )
                        return res['secure_url']
                    except Exception as e:
                        return f"Error: {e}"

                df_u['Foto_Link_Cloudinary'] = df_u.apply(procesar_imagen_cloudinary, axis=1)
                
                cols = ['Hora', 'Tipo', 'Etiqueta_Foto', 'Latitud', 'Longitud', 'Zona', 'Foto_Link_Cloudinary']
                for c in cols:
                    if c not in df_u.columns: df_u[c] = ""
                
                datos_finales = df_u[cols].values.tolist()
                
                try:
                    ws = sh.add_worksheet(title=str(usuario), rows=1000, cols=10)
                    ws.append_row(cols)
                except:
                    ws = sh.worksheet(str(usuario))
                
                ws.append_rows(datos_finales)
                pasos_completados += len(df_u)
                bar.progress(min(pasos_completados / total_pasos, 1.0))

            status.write("🗑️ Limpiando Airtable...")
            ids = [r['id'] for r in records]
            table.batch_delete(ids)
            
            status.update(label="¡Completado!", state="complete")
            st.success(f"Archivo guardado: {sh.url}")
            st.balloons()

