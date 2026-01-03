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
        
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import PolyLineTextPath
import math

# --- Función Auxiliar: Distancia Real (Haversine) ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- Función Auxiliar: Extraer URL de Foto de forma segura ---
def extraer_url_foto(valor_celda):
    if not valor_celda:
        return None
    # Caso 1: Es una lista de Airtable (formato estándar)
    if isinstance(valor_celda, list) and len(valor_celda) > 0:
        return valor_celda[0].get('url')
    # Caso 2: Es un diccionario directo
    if isinstance(valor_celda, dict):
        return valor_celda.get('url')
    # Caso 3: Es una cadena de texto (URL directa)
    if isinstance(valor_celda, str) and (valor_celda.startswith('http') or valor_celda.startswith('https')):
        return valor_celda
    return None

# --- SECCIÓN 4: MAPA ESTRATÉGICO MAESTRO ---
if not df_gps.empty:
    st.markdown("---")
    
    # 1. NORMALIZACIÓN DE COLUMNAS
    df_gps.columns = [c.lower() for c in df_gps.columns]
    
    col_lat = 'latitud' if 'latitud' in df_gps.columns else None
    col_lon = 'longitud' if 'longitud' in df_gps.columns else None
    col_user = 'usuario' if 'usuario' in df_gps.columns else None
    col_foto = 'foto' if 'foto' in df_gps.columns else None
    col_hora = 'hora' if 'hora' in df_gps.columns else None

    if col_lat and col_lon:
        df_gps[col_lat] = pd.to_numeric(df_gps[col_lat], errors='coerce')
        df_gps[col_lon] = pd.to_numeric(df_gps[col_lon], errors='coerce')
        df_gps = df_gps.dropna(subset=[col_lat, col_lon])
    
    if col_hora in df_gps.columns:
        df_gps['hora_dt'] = pd.to_datetime(df_gps[col_hora], format='%H:%M:%S', errors='coerce')
        df_gps = df_gps.sort_values(by=[col_user, 'hora_dt'])

    # 2. CONTROLES SIDEBAR
    with st.sidebar:
        st.header("⚙️ Configuración")
        tipo_mapa = st.radio("Vista de Mapa", ["Calle", "Satélite"])
        modo_reporte = st.checkbox("📑 Activar Modo Reporte (PDF)")
        
        raw_users = df_gps[col_user].dropna().unique().tolist() if col_user else []
        repartidores_sel = st.multiselect("Filtrar Repartidores", sorted([str(u) for u in raw_users]), default=raw_users)

    df_filtrado = df_gps[df_gps[col_user].isin(repartidores_sel)]

    if not df_filtrado.empty:
        # Crear Mapa
        m = folium.Map(location=[df_filtrado[col_lat].mean(), df_filtrado[col_lon].mean()], zoom_start=15, zoom_control=False)
        
        if tipo_mapa == "Satélite":
            folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
        else:
            folium.TileLayer('OpenStreetMap').add_to(m)

        colores_vibrantes = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#FF8C00', '#7FFF00']
        resumen_datos = []

        for i, nombre in enumerate(repartidores_sel):
            color = colores_vibrantes[i % len(colores_vibrantes)]
            u_data = df_filtrado[df_filtrado[col_user] == nombre].reset_index(drop=True)
            distancia_total = 0.0
            
            if len(u_data) > 0:
                coords = u_data[[col_lat, col_lon]].values.tolist()
                
                # A. LÍNEA CON SOMBRA
                if len(coords) > 1:
                    folium.PolyLine(coords, color='black', weight=6, opacity=0.4).add_to(m)
                    linea = folium.PolyLine(coords, color=color, weight=2.5, opacity=1).add_to(m)
                    folium.plugins.PolyLineTextPath(linea, '                ►                ', repeat=True, offset=8, 
                                                    attributes={'fill': color, 'font-weight': 'bold', 'font-size': '20', 'stroke': 'black', 'stroke-width': '0.5'}).add_to(m)

                # B. HITOS, DISTANCIA Y PARADAS
                ultima_hora_hito = None
                for j in range(len(u_data)):
                    row = u_data.iloc[j]
                    
                    if j < len(u_data) - 1:
                        p_next = u_data.iloc[j+1]
                        distancia_total += calcular_distancia(row[col_lat], row[col_lon], p_next[col_lat], p_next[col_lon])
                        t_parada = (p_next['hora_dt'] - row['hora_dt']).total_seconds() / 60
                        if t_parada >= 5:
                            folium.Marker([row[col_lat], row[col_lon]], icon=folium.DivIcon(html='<div style="font-size:18pt">🚩</div>'),
                                          popup=f"🛑 Parada: {int(t_parada)} min").add_to(m)

                    if ultima_hora_hito is None or (row['hora_dt'] - ultima_hora_hito).total_seconds() >= 900:
                        folium.Marker([row[col_lat], row[col_lon]], 
                                      icon=folium.DivIcon(html=f'<div style="text-align:center;"><div style="font-size:16pt;filter:drop-shadow(1px 1px 1px black);">📍</div><div style="font-size:8pt;color:white;background:rgba(0,0,0,0.7);padding:1px 3px;border-radius:3px;">{row[col_hora][:5]}</div></div>')).add_to(m)
                        ultima_hora_hito = row['hora_dt']

                # C. EXTREMOS (📌 y 🏁)
                r_ini, r_fin = u_data.iloc[0], u_data.iloc[-1]
                folium.Marker([r_ini[col_lat], r_ini[col_lon]], icon=folium.DivIcon(html='<div style="font-size:24pt;filter:drop-shadow(2px 2px 2px black);">📌</div>'), popup=f"SALIDA: {r_ini[col_hora]}").add_to(m)
                folium.Marker([r_fin[col_lat]+0.00002, r_fin[col_lon]+0.00002], icon=folium.DivIcon(html='<div style="font-size:24pt;filter:drop-shadow(2px 2px 2px black);">🏁</div>'), popup=f"LLEGADA: {r_fin[col_hora]}").add_to(m)

                # D. FOTOS EN EL MAPA (Miniaturas)
                if col_foto:
                    for _, f_row in u_data.iterrows():
                        url_mapa = extraer_url_foto(f_row.get(col_foto))
                        if url_mapa:
                            folium.Marker([f_row[col_lat], f_row[col_lon]], 
                                          icon=folium.DivIcon(html=f'<div style="width:50px;height:50px;border:2px solid {color};background:white;padding:2px;"><img src="{url_mapa}" width="46" height="46" style="object-fit:cover;"></div>'),
                                          popup=folium.Popup(f'<img src="{url_mapa}" width="200">', max_width=200)).add_to(m)

                resumen_datos.append({"Repartidor": nombre, "Salida": r_ini[col_hora], "Llegada": r_fin[col_hora], "KM": round(distancia_total, 2)})

        m.fit_bounds(df_filtrado[[col_lat, col_lon]].values.tolist())
        st_folium(m, width="100%", height=650)

        # 📄 SECCIÓN DE REPORTE (Aquí vive la Galería de Testigos)
        if modo_reporte:
            st.markdown("### 📋 Resumen de Jornada")
            st.table(pd.DataFrame(resumen_datos))
            
            st.write("### 📸 Galería de Testigos")
            # Filtrar filas que tengan contenido en la columna foto
            df_con_fotos = df_filtrado[df_filtrado[col_foto].notna()]
            
            if not df_con_fotos.empty:
                cols_gal = st.columns(4)
                contador = 0
                for _, row_f in df_con_fotos.iterrows():
                    url_f = extraer_url_foto(row_f[col_foto])
                    if url_f:
                        with cols_gal[contador % 4]:
                            st.image(url_f, caption=f"{row_f[col_user]} - {row_f[col_hora]}")
                        contador += 1
            else:
                st.info("No se encontraron registros con fotografías para este reporte.")
    else:
        st.info("Selecciona repartidores en la barra lateral.")
              
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

